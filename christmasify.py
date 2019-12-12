import os
import pandas as pd
import numpy as np
import itertools
from scipy import spatial
import scipy.ndimage
import argparse
from matplotlib.path import Path
from zipfile import ZipFile 

from ply_io import read_ply, write_ply

import warnings
warnings.filterwarnings('ignore')

def rotation_matrix(rot=[0, 0, 0], tra=[0, 0, 0]):
    
    xA, yA, zA = rot
    xT, yT, zT = tra
    
    rX = np.matrix([[1, 0, 0, xT], [0, np.cos(xA), -np.sin(xA), 0], [0, np.sin(xA), np.cos(xA), 0], [0, 0, 0, 1]])
    rY = np.matrix([[np.cos(yA), 0, np.sin(yA), 0], [0, 1, 0, yT], [-np.sin(yA), 0, np.cos(yA), 0], [0, 0, 0, 1]])
    rZ = np.matrix([[np.cos(zA), -np.sin(zA), 0, 0], [np.sin(zA), np.cos(zA), 0, 0], [0, 0, 1, zT], [0, 0, 0, 1]])

    return np.dot(rZ, np.dot(rY, rX))

def generate_sphere(radius):

    d = np.deg2rad(np.arange(0, 360, 5))
    template = np.zeros((len(d)*len(d), 4))
    v = np.array([0, radius, 0, 1])

    for i, (a, z) in enumerate(itertools.permutations(d, 2)):

        R = rotation_matrix(rot=[z, 0, a])
        v_ = np.array(np.dot(R, v))[0]
        template[i, :] = v_

    return template[:np.where(template[:, 3] == 1)[0].max(), :] 
    
# some arguments
parser = argparse.ArgumentParser()
parser.add_argument('--tree', type=str, required=True, help='path to tree')
parser.add_argument('--sketchfab', action='store_true', help='make sketchfab ready')
parser.add_argument('--zmin', default=0., type=float, help='bottom of the decorations')
parser.add_argument('--vertical_spacing', default=.5, type=float, help='spacing between baubaul layers')
parser.add_argument('--replace-brown', action='store_true', help='replace the existing tree colour')
parser.add_argument('--snow', action='store_true', help='add a snowy ground')
parser.add_argument('--verbose', action='store_true', help='add a snowy ground')
args = parser.parse_args()

# read in tree
if args.verbose: print 'reading in point cloud:', args.tree
folder, tree = os.path.split(args.tree)
if tree.endswith('.ply'):
    tree_pc = read_ply(args.tree)
else:
    tree_pc = pd.read_csv(args.tree, sep=' ')
    tree_pc.columns = [c.lower() if '//' not in c else c[2:].lower() for c in tree_pc.columns]

# check and add colour if only xyz  
tree_pc.rename(columns={'r':'red', 'g':'green', 'b':'blue'}, inplace=True)
if 'red' not in tree_pc.columns or args.replace_brown:
    if args.verbose: print 'painting the tree brown...'
    tree_pc.loc[:, 'red'] = 160
    tree_pc.loc[:, 'green'] = 82
    tree_pc.loc[:, 'blue'] = 45
    
tree_pc.loc[:, 'zz'] = (tree_pc.z // args.vertical_spacing) * args.vertical_spacing

baubaul = generate_sphere(.5)
light = generate_sphere(.1)

# empty arrays to store baubals and lights
baubals = np.empty((0, 7))
lights = np.empty((0, 8))

# loop over slices in tree to add baubauls and lights
if args.verbose: print 'adding lights and baubauls'
for z in tree_pc.zz.unique():
    
    if z < args.zmin: continue
    
    z_slice = tree_pc[tree_pc.zz == z]
    if len(z_slice) < 10: continue
    hull = spatial.ConvexHull(z_slice[['x', 'y']])
        
    for baubal_ix in np.random.choice(hull.vertices, size=min(5, len(hull.vertices))):

        # generate baubaul for layer (1 per layer)
        baubal_xy = z_slice[['x', 'y']].loc[z_slice.index[baubal_ix]]
        XY = np.identity(4)
        XY[:2, 3] = baubal_xy
        XY[2, 3] = z
        bb_ = np.dot(XY, baubaul.T).T
        rgb = np.repeat(np.random.randint(0, 255, size=3), len(bb_), axis=0).reshape(-1, len(bb_)).T
        baubals = np.vstack([baubals, np.hstack([bb_, rgb])])

    # generate lights
    n_lights = int(hull.volume) / 20
    x_p = z_slice.x.min() + (np.ptp(z_slice.x.values) * np.random.random_sample(size=n_lights))
    y_p = z_slice.y.min() + (np.ptp(z_slice.y.values) * np.random.random_sample(size=n_lights))
    points = np.vstack([x_p.T, y_p.T]).T
    
    # ensure they're inside the tree
    hull_path = Path( z_slice[['x', 'y']].loc[z_slice.index[hull.vertices]] )
    in_hull = [hull_path.contains_point((x, y)) for x, y in points]
    points = points[np.where(in_hull)]
    
    # randomise z position a little
    for x, y in points:
        
        XY = np.identity(4)
        XY[:2, 3] = x, y
        XY[2, 3] = z + np.random.random() * args.vertical_spacing
        if XY[2, 3] > tree_pc.z.max(): continue
        light_ = np.dot(XY, light.T).T
        rgb = np.repeat([255, 248, 220], len(light_), axis=0).reshape(-1, len(light_)).T
        on = np.zeros((len(light_), 1)) + np.random.randint(1, high=3)
        lights = np.vstack([lights, np.hstack([light_, rgb, on])])
        
    if args.verbose: print '...and more', np.random.choice(['lights', 'baubauls', 'mince pies'], p=[.4, .4, .2]), '...'
        
# concatenate all baubauls and lights
baubals = pd.DataFrame(baubals, columns=['x', 'y', 'z', 'a', 'red', 'green', 'blue'])
lights = pd.DataFrame(lights, columns=['x', 'y', 'z', 'a', 'red', 'green', 'blue', 'on'])

if args.snow:
    if args.verbose: print 'adding a snow field'
    X, Y, Z = np.meshgrid(np.arange(tree_pc.x.min(), tree_pc.x.max(), .1),
                       np.arange(tree_pc.y.min(), tree_pc.y.max(), .1),
                       tree_pc.z.min())
    Z += np.random.normal(scale=.5, size=Z.shape)
    Z = scipy.ndimage.filters.gaussian_filter(Z, 10, mode='reflect')
    snow = pd.DataFrame(data=np.vstack([X.flatten(), Y.flatten(), Z.flatten()]).T, columns=['x', 'y', 'z'])
    snow.loc[:, 'red'] = 255
    snow.loc[:, 'green'] = 255
    snow.loc[:, 'blue'] = 255
    tree_pc = tree_pc.append(snow)

tree_pc = tree_pc.append(baubals[['x', 'y', 'z', 'red', 'green', 'blue']])
tree_pc.loc[:, 'on'] = 0
tree_pc = tree_pc.append(lights[['x', 'y', 'z', 'red', 'green', 'blue', 'on']])

if args.sketchfab and len(tree_pc) > 3e6:
    if args.verbose: print 'thinning from', len(tree_pc), 'to 2.5M points'
    tree_pc = tree_pc.sample(n=int(3e6))
    
for i, lo in enumerate([1, 2]): 
    write_ply(os.path.join(folder, 'xmas_tree_pc{}.ply'.format(i)), 
              tree_pc[tree_pc.on.isin([0, lo])][['x', 'y', 'z', 'red', 'green', 'blue']])
    
if args.sketchfab:
    if args.verbose: print 'preparing sketchfab upload'

    with open(os.path.join(folder, 'sketchfab.timeframe'), 'w') as fh:
        fh.write('1 xmas_tree_pc_0.ply\n')
        fh.write('1 xmas_tree_pc_1.ply\n')
              
    with ZipFile(os.path.join(folder, 'my-awesome-christmas-tree.zip'),'w') as zip: 
        # writing each file one by one 
        zip.write(os.path.join(folder, 'sketchfab.timeframe'))
        zip.write(os.path.join(folder, 'xmas_tree_pc0.ply'))
        zip.write(os.path.join(folder, 'xmas_tree_pc1.ply'))

    if os.stat(os.path.join(folder, 'my-awesome-christmas-tree.zip')).st_size > 180000000:
	print '!!! SketchFab file to big either reduce tree point density or increase vertical spacing !!!'   
               
