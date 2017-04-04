import pandas as pd
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.cm as cm
from matplotlib.colors import Normalize
from matplotlib.collections import PatchCollection
from mpl_toolkits.basemap import Basemap
from shapely.geometry import Point, Polygon, MultiPoint, MultiPolygon
from shapely.prepared import prep
from pysal.esda.mapclassify import Natural_Breaks as nb
from descartes import PolygonPatch
import fiona
from itertools import chain
import locale

#Read data on house prices and their coordinates location
prices = pd.read_csv('data/LocationPrice.csv')

#Shape file containing ward boundaries downloaded from http://senstitivecities.com (http://sensitivecities.com/extra/london.zip)
shp = fiona.open('data/london_wards.shp')
bds = shp.bounds
shp.close()
extra = 0.01
ll = (bds[0], bds[1])
ur = (bds[2], bds[3])
coords = list(chain(ll, ur))
w, h = coords[2] - coords[0], coords[3] - coords[1]

#Create Basemap instance
m = Basemap(
    projection='tmerc',
    lon_0=-2.,
    lat_0=49.,
    ellps = 'WGS84',
    llcrnrlon=coords[0] - extra * w,
    llcrnrlat=coords[1] - extra + 0.01 * h,
    urcrnrlon=coords[2] + extra * w,
    urcrnrlat=coords[3] + extra + 0.01 * h,
    lat_ts=0,
    resolution='i',
    suppress_ticks=True)
m.readshapefile(
    'data/london_wards',
    'london',
    color='none',
    zorder=2)
    
#create a map dataframe
df_map = pd.DataFrame({
    'poly': [Polygon(xy) for xy in m.london],
    'ward_name': [ward['NAME'] for ward in m.london_info]})

#create Point objects in map coordinates from dataframe lon and lat values
map_points_price = pd.Series(
    [Point(m(mapped_x, mapped_y)) for mapped_x, mapped_y in zip(prices['Longitude'], prices['Latitude'])])
price = prices['Price']
points_price = MultiPoint(list(map_points_price.values))

#create a dictionary with price points for each postcode location point and their average price
d_price={}
count = {}
for i in range(len(points_price)):
    if (points_price[i].x, points_price[i].y) in d_price:
        count[(points_price[i].x, points_price[i].y)] += 1
        d_price[(points_price[i].x, points_price[i].y)] += price[i]
    else:
        count[(points_price[i].x, points_price[i].y)] = 1
        d_price[(points_price[i].x, points_price[i].y)] = price[i]

for i in d_price:
    d_price[i] = d_price[i] / count[i]

wards_polygon = prep(MultiPolygon(list(df_map['poly'].values)))
#just get points that fall within London's boundary
price_points = filter(wards_polygon.contains, points_price)

#Convenience functions for working with colour ramps and bars (made by Stephan Hügel, 2015)
def colorbar_index(ncolors, cmap, labels=None, **kwargs):
    """
    This is a convenience function to stop you making off-by-one errors
    Takes a standard colour ramp, and discretizes it,
    then draws a colour bar with correctly aligned labels
    """
    cmap = cmap_discretize(cmap, ncolors)
    mappable = cm.ScalarMappable(cmap=cmap)
    mappable.set_array([])
    mappable.set_clim(-0.5, ncolors+0.5)
    colorbar = plt.colorbar(mappable, **kwargs)
    colorbar.set_ticks(np.linspace(0, ncolors, ncolors))
    colorbar.set_ticklabels(range(ncolors))
    if labels:
        colorbar.set_ticklabels(labels)
    return colorbar

def cmap_discretize(cmap, N):
    """
    Return a discrete colormap from the continuous colormap cmap.
        cmap: colormap instance, eg. cm.jet. 
        N: number of colors.
    Example
        x = resize(arange(100), (5,100))
        djet = cmap_discretize(cm.jet, 5)
        imshow(x, cmap=djet)
    """
    if type(cmap) == str:
        cmap = get_cmap(cmap)
    colors_i = np.concatenate((np.linspace(0, 1., N), (0., 0., 0., 0.)))
    colors_rgba = cmap(colors_i)
    indices = np.linspace(0, 1., N + 1)
    cdict = {}
    for ki, key in enumerate(('red', 'green', 'blue')):
        cdict[key] = [(indices[i], colors_rgba[i - 1, ki], colors_rgba[i, ki]) for i in xrange(N + 1)]
    return matplotlib.colors.LinearSegmentedColormap(cmap.name + "_%d" % N, cdict, 1024)
    
#Let's make the map
df_map['Price'] = df_map['poly'].map(lambda x: np.mean([d_price[(i.x, i.y)] for i in filter(prep(x).contains, price_points)]))

#Calculate Jenks natural breaks for price
breaks = nb(
    df_map[df_map['Price'].notnull()].Price.values,
    initial=300,
    k=5)

#the notnull method lets us match indices when joining
jb = pd.DataFrame({'jenks_bins': breaks.yb}, index=df_map[df_map['Price'].notnull()].index)
df_map = df_map.join(jb)
df_map.jenks_bins.fillna(-1, inplace=True)

#Let's convert prices in a more readable format (e.g GBP 1,500,000)
locale.setlocale(locale.LC_ALL, '')
locale.currency(7000000, grouping=True )

jenks_labels = [u"\xA3" + "%s (%s wards)" % (locale.currency(b, grouping = True)[1:-3], c) for b, c in zip(
    breaks.bins, breaks.counts)]
jenks_labels.insert(0, 'No property sales registered\n(%s wards)' % len(df_map[df_map['Price'].isnull()]))

plt.clf()
fig = plt.figure()
ax = fig.add_subplot(111, axisbg='w', frame_on=False)

#use a yellow colour ramp
cmap = plt.get_cmap('YlOrBr')
# draw wards with grey outlines
df_map['patches'] = df_map['poly'].map(lambda x: PolygonPatch(x, ec='#555555', lw=.2, alpha=1., zorder=4))
pc = PatchCollection(df_map['patches'], match_original=True)
#colour map onto the patches
norm = Normalize()
pc.set_facecolor(cmap(norm(df_map['jenks_bins'].values)))
ax.add_collection(pc)

#Add colour bar
cb = colorbar_index(ncolors=len(jenks_labels), cmap=cmap, shrink=0.5, labels=jenks_labels)
cb.ax.tick_params(labelsize=6)

#Show highest prices
highest = '\n'.join(
    value[1] for _, value in df_map[(df_map['jenks_bins'] == 4)][:10].sort().iterrows())
highest = 'Most Expensive Wards:\n\n' + highest
#for precise y coordinate alignment
details = cb.ax.text(
    -1., 0 - 0.007,
    highest,
    ha='right', va='bottom',
    size=5,
    color='#555555')

#show scale
m.drawmapscale(
    coords[0] + 0.08, coords[1] + 0.015,
    coords[0], coords[1],
    10.,
    barstyle='fancy', labelstyle='simple',
    fillcolor1='w', fillcolor2='#555555',
    fontcolor='#555555',
    zorder=5)
# his will set the image width to 722px and height to 525 px at 100dpi
plt.tight_layout()
fig.set_size_inches(7.22, 5.25)
plt.savefig('data/london_prices_choro.png', dpi=100, alpha=True)
