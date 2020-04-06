import time
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
import cv2

t1=time.time()
f,ax=plt.subplots(1,1,figsize=(10,6),dpi=100)
ax.set_xlim(73.4997347, 134.7754563)
ax.set_ylim(17.7,53.560815399999996)    

#Plot China
img=mpimg.imread('China.png')      
ax.imshow(img,extent=(73.4997347, 134.7754563, 17.7, 53.560815399999996))  ### ax.imshow()
#cv2.rectangle(img, [90,40], [100,50], (0, 255, 0), 2)
#Highlight Heilongjiang
dfprovinces=pd.read_csv("Provinces.csv.gz")
dfHighlight=dfprovinces[(dfprovinces["name"]=="Beijing")]
for row in dfHighlight.itertuples():        
    lonsL=eval(row.lons)
    latsL=eval(row.lats)
    for i in range(len(lonsL)):
        ax.fill(eval(lonsL[i]),eval(latsL[i]),facecolor="red",edgecolor="k",alpha=1.0, linewidth=0.1)       

#Plot heatmap with colorbar
data=np.array([[0.8, 2.4, 2.5, 3.9, 0.0, 4.0, 0.0],
                [2.4, 0.0, 4.0, 1.0, 2.7, 0.0, 0.0],
                [1.1, 2.4, 0.8, 4.3, 1.9, 4.4, 0.0],
                [0.6, 0.0, 0.3, 0.0, 3.1, 0.0, 0.0],
                [0.7, 1.7, 0.6, 2.6, 2.2, 6.2, 0.0],
                [1.3, 1.2, 0.0, 0.0, 0.0, 3.2, 5.1],
                [0.1, 2.0, 0.0, 1.4, 0.0, 1.9, 6.3]])

# mask some 'bad' data, in your case you would have: data == 0
data = np.ma.masked_where(data < 0.05, data)

#cmap = plt.cm.OrRd
#cmap.set_bad(color='blank')

#img=ax.imshow(data, extent=[90,120,30,45], 
#              origin='lower', interpolation='None', 
#              cmap='viridis',alpha=0.4,zorder=1,
#             )  ## interpolation="bicubic" # 'viridis'
#
#plt.colorbar(img,orientation="vertical")
from pylab import figure, cm
from matplotlib.colors import LogNorm
# C = some matrix
#ax = f.add_axes([0.17, 0.02, 0.72, 0.79])
#axcolor = f.add_axes([0.90, 0.02, 0.03, 0.79])
im = ax.matshow(data, 
                extent=[90,120,30,45], 
                cmap='viridis')  #  norm=LogNorm(vmin=0.01, vmax=10)
t = [0.01, 0.1, 0.2, 0.4, 0.6, 0.8, 10.0]
plt.colorbar(im, format='$%.2f$') # ticks=t,
plt.show()


t2=time.time()
print(t2-t1)