import os
import pandas as pd
import glob
from datetime import date
import numpy as np
from sklearn import preprocessing

from mplsoccer import Pitch, VerticalPitch
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.patheffects as path_effects
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
import matplotlib.font_manager as fm
from matplotlib.legend_handler import HandlerLine2D
from matplotlib.patches import FancyArrowPatch

from PIL import Image
from tempfile import NamedTemporaryFile
import urllib
import os

github_url = 'https://github.com/google/fonts/blob/main/ofl/poppins/Poppins-Bold.ttf'
url = github_url + '?raw=true'

response = urllib.request.urlopen(url)
f = NamedTemporaryFile(delete=False, suffix='.ttf')
f.write(response.read())
f.close()

bold = fm.FontProperties(fname=f.name)

github_url = 'https://github.com/google/fonts/blob/main/ofl/poppins/Poppins-Regular.ttf'
url = github_url + '?raw=true'

response = urllib.request.urlopen(url)
f = NamedTemporaryFile(delete=False, suffix='.ttf')
f.write(response.read())
f.close()

reg = fm.FontProperties(fname=f.name)

path_eff = [path_effects.Stroke(linewidth=3.5, foreground='#ffffff'),
            path_effects.Normal()]

hcolors = ['#ffffff', '#d5dcdc', '#acb9b9', '#839696', '#597373', '#305050', '#062d2d']
hcmap = ListedColormap(hcolors, name="hcmap")
hcmapr = hcmap.reversed()

acolors = ['#052d2d', '#094329', '#0b5825', '#0e6e21', '#10841d', '#129919', '#15af15']
acmap = ListedColormap(acolors, name="acmap")
acmapr = acmap.reversed()

def get_PNdata(tl, rp, min_min, max_min, team):
  df = tl.copy()
  df2 = rp.copy()

  pos = df2[df2['Team']==team]
  pos['Position (in match)'].fillna('SUBS', inplace=True)
  pos = pos[pos['MoP']>0].reset_index(drop=True)
  pos['Status'] = 'Full'
  #pos['Nick'] = pos['Name'].str.split(' ').str[0]

  for i in range(len(pos)):
    if (pos['MoP'][i] < 90) and (pos['Position (in match)'][i]!='SUBS'):
      pos['Status'][i] = 'Sub Out'
    elif (pos['MoP'][i] < 90) and (pos['Position (in match)'][i]=='SUBS'):
      pos['Status'][i] = 'Sub In'
    else:
      pos['Status'][i] = 'Full'
            
  pos = pos[['No. Punggung', 'Name', 'Position (in match)', 'Status', 'Nick']]
  pos.rename({'Name':'Passer', 'Position (in match)':'Pos', 'No. Punggung':'No'}, axis='columns',inplace=True)

  df['Minx'] = df['Min'].str.split(' :').str[0]
  df['Mins'] = df['Minx'].str.split('+').str[0]
  df['Mins'].fillna(df['Minx'], inplace=True)
  df['Mins'] = df['Mins'].astype(float)
  pos['No'] = pos['No'].astype(int)

  firstsub = df[(df['Action']=='subs') | (df['Action']=='red card')]
  firstsub = firstsub[firstsub['Team']==team]
  listmin = list(firstsub['Mins'])
  df = df[df['Act Zone'].notna()]

  minmin = min_min
  maxmin = max_min+1

  data = df[df['Action']=='passing']
  data = data[data['Team']==team]
  data = data[data['Mins']<=maxmin][data['Mins']>=minmin]
  pascnt = data[['Act Name', 'Act Zone', 'Pas Name']]
  pascnt = pascnt.groupby(['Act Name','Pas Name'], as_index=False).count()
  pascnt.rename({'Act Name':'Passer','Pas Name':'Recipient','Act Zone':'Count'}, axis='columns',inplace=True)
  highest_passes = pascnt['Count'].max()
  pascnt['passes_scaled'] = pascnt['Count']/highest_passes

  data2 = df[df['Team']==team]
  data2 = data2[data2['Mins']<=maxmin][data2['Mins']>=minmin]
  avgpos = data2[['Act Name', 'Act Zone']]
  temp = avgpos['Act Zone'].apply(lambda x: pd.Series(list(x)))
  avgpos['X'] = temp[0]
  avgpos['Y'] = temp[1]
  avgpos['Y'] = avgpos['Y'].replace({'A':10,'B':30,'C':50,'D':70,'E':90})
  avgpos['X'] = avgpos['X'].replace({'1':8.34,'2':25.34,'3':42.34,
                                     '4':59.34,'5':76.34,'6':93.34})
  avgpos = avgpos[['Act Name','X','Y']]
  avgpos = avgpos.groupby(['Act Name'], as_index=False).mean()
  avgpos.rename({'Act Name':'Passer'}, axis='columns',inplace=True)
  avgpos['Recipient'] = avgpos['Passer']
  avgpos = pd.merge(avgpos, pos, on='Passer', how='left')

  pass_between = pd.merge(pascnt, avgpos.drop(['Recipient'], axis=1), on='Passer', how='left')
  pass_between = pd.merge(pass_between, avgpos.drop(['Passer'], axis=1), on='Recipient', how='left', suffixes=['','_end']).drop('Pos_end', axis=1)

  passtot = pass_between[['Passer', 'Count']]
  passtot = passtot.groupby('Passer', as_index=False).sum()
  passtot.rename({'Count':'Total'}, axis='columns',inplace=True)
  passtot['size'] = (passtot['Total']/max(passtot['Total']))*3000

  #pass_between = pass_between[pass_between['Count']>=min_pass]
  pass_between = pd.merge(pass_between, passtot, on='Passer', how='left')

  return pass_between, listmin
  

def plot_PN(data, min_pass, team, min_min, max_min, match, gw):
  pass_between = data.copy()
  fig, ax = plt.subplots(figsize=(20, 20), dpi=500)
  fig.patch.set_facecolor('#ffffff')
  ax.set_facecolor('#ffffff')

  pitch = Pitch(pitch_type='wyscout', pitch_color='#ffffff', line_color='#000000', pad_bottom=13, pad_top=12,
                corner_arcs=True, stripe=True, stripe_color='#fcf8f7', goal_type='box', linewidth=3.5)
  pitch.draw(ax=ax)

  cmap = plt.cm.get_cmap(hcmap)
  for row in pass_between.itertuples():
    if row.Count > min_pass:
      if abs(row.Y_end - row.Y) > abs(row.X_end - row.X):
        if row.Passer > row.Recipient:
          x_shift, y_shift = 0, 2
        else:
          x_shift, y_shift = 0, -2
      else:
        if row.Passer > row.Recipient:
          x_shift, y_shift = 2, 0
        else:
          x_shift, y_shift = -2, 0

      ax.plot([row.X_end+x_shift, row.X+x_shift],[row.Y_end+y_shift, row.Y+y_shift],
              color=cmap(row.passes_scaled), lw=3, alpha=row.passes_scaled)

      ax.annotate('', xytext=(row.X_end+x_shift, row.Y_end+y_shift),
                  xy=(row.X_end+x_shift+((row.X-row.X_end)/2),
                      row.Y_end+y_shift+((row.Y-row.Y_end)/2)),
                  arrowprops=dict(arrowstyle='->', color=cmap(row.passes_scaled),
                                  lw=3, alpha=row.passes_scaled), size=25)
  avgpos = pass_between[['Passer', 'X', 'Y', 'size', 'No', 'Pos', 'Status', 'Nick']]
  avgpos = avgpos.groupby(['Passer', 'X', 'Y', 'size', 'No', 'Pos', 'Status', 'Nick'], as_index=False).nunique()
      
  for i in range(len(avgpos)):
    if (avgpos['Status'][i]=='Full'):
      pitch.scatter(avgpos['X'][i], avgpos['Y'][i], s = avgpos['size'][i], zorder=10,
                    color='#ffffff', edgecolors='#000000', linewidth=5, ax=ax)
    elif (avgpos['Status'][i]=='Sub In'):
      pitch.scatter(avgpos['X'][i], avgpos['Y'][i], s = avgpos['size'][i], zorder=10,
                    color='#ffffff', edgecolors='#000000', linewidth=5, ax=ax)
      pitch.scatter(avgpos['X'][i]-1.5, avgpos['Y'][i]-2, s = 300, zorder=10,
                    color='#7ed957', edgecolors='#000000', linewidth=2, ax=ax, marker='^')
    else:
      pitch.scatter(avgpos['X'][i], avgpos['Y'][i], s = avgpos['size'][i], zorder=10,
                    color='#ffffff', edgecolors='#000000', linewidth=5, ax=ax)
      pitch.scatter(avgpos['X'][i]+1.5, avgpos['Y'][i]+2, s = 300, zorder=10,
                    color='#e66009', edgecolors='#000000', linewidth=2, ax=ax, marker='v')
    pitch.annotate(avgpos['No'][i], xy=(avgpos['X'][i], avgpos['Y'][i]), c='#000000', va='center', zorder=11,
                   ha='center', size=16, weight='bold', ax=ax, path_effects=path_eff)
    pitch.annotate(avgpos['Nick'][i], xy=(avgpos['X'][i], avgpos['Y'][i]+5), c='#000000', va='center', zorder=11,
                   ha='center', size=14, weight='bold', ax=ax, path_effects=path_eff)
              
  if (min_min == 0):
    min_mins = min_min+1
  else:
    min_mins = min_min

  if (max_min == 91):
    max_mins = max_min-1
  else:
    max_mins = max_min

  anot_x = [75, 79, 84, 90]
  anot_y = [105.35, 105.25, 105.15, 105]
  anot_s = [500, 1000, 1500, 2000]
  for x, y, s in zip(anot_x, anot_y, anot_s):
    ax.scatter(x, y, s=s, c='#ffffff', lw=5,
               marker='o', edgecolors='#000000')
  pitch.arrows(74, 110, 92, 110, width=2, color='#000000',
               headwidth=7, ax=ax)
  ax.text(75, 112, '1 pass', ha='center', fontproperties=bold, color='#000000', size='16', va='center')
  ax.text(90, 112, '40+ passes', ha='center', fontproperties=bold, color='#000000', size='16', va='center')

  anot_x1 = [8, 12, 16, 20]
  anot_x2 = [11, 15, 19, 23]
  anot_a = [0.7, 0.8, 0.9, 1]
  anot_c = ['#839696','#597373','#305050','#062d2d']
  for x1, x2, a, c in zip(anot_x1, anot_x2, anot_a, anot_c):
    pitch.lines(x1, 109, x2, 102, color=c,
                zorder=1, lw=4, alpha=a, ax=ax)
  pitch.arrows(7, 110, 23, 110, width=2, color='#000000',
               headwidth=7, ax=ax)
  if (min_pass == 1):
    ax.text(8, 112, str(min_pass)+' pass', ha='center', fontproperties=bold, color='#000000', size='16', va='center')
  else:
    ax.text(8, 112, str(min_pass)+' passes', ha='center', fontproperties=bold, color='#000000', size='16', va='center')
  ax.text(23, 112, '10+ passes', ha='center', fontproperties=bold, color='#000000', size='16', va='center')

  pitch.scatter(40, 106, s = 800, zorder=10, color='#7ed957',
                edgecolors='#000000', linewidth=4, ax=ax, marker='^')
  ax.text(40, 112, 'Subbed In', ha='center', fontproperties=bold, color='#000000', size='16', va='center')
  pitch.scatter(60, 106, s = 800, zorder=10, color='#e66009',
                edgecolors='#000000', linewidth=4, ax=ax, marker='v')
  ax.text(60, 112, 'Subbed Out', ha='center', fontproperties=bold, color='#000000', size='16', va='center')

  ax.text(0, -8, 'PASSING NETWORK', ha='left', fontproperties=bold, color='#000000', size='22', va='center')
  ax.text(0, -4, team.upper()+' | MINUTES: '+str(min_mins)+'-'+str(max_mins), ha='left', fontproperties=reg, color='#000000', size='18', va='center')
  ax.text(100, -8, match.upper(), ha='right', fontproperties=reg, color='#000000', size='18', va='center')
  ax.text(100, -4, gw, ha='right', fontproperties=reg, color='#000000', size='18', va='center')
  
  plt.savefig('pnet.jpg', dpi=500, bbox_inches='tight', facecolor=fig.get_facecolor(), edgecolor='none')
  
  return fig
