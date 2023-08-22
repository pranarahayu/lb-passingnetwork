import sys

sys.path.append("xgmodel.py")
import xgmodel
from xgmodel import calculate_xG
from xgmodel import xgfix

sys.path.append("psxgmodel.py")
import psxgmodel
from psxgmodel import calculate_PSxG
from psxgmodel import psxgfix

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

path_eff = [path_effects.Stroke(linewidth=2, foreground='#f2ff00'),
            path_effects.Normal()]

hcolors = ["#052d2d", "#06372b", "#074129", "#094b27", "#0a5526",'#0b5f24','#0c6922',
           '#0e7320', '#0e7320','#10871c','#139b19', '#14a517', '#15af15']
hcmap = ListedColormap(hcolors, name="hcmap")
hcmapr = hcmap.reversed()

acolors = ['#052d2d', '#094329', '#0b5825', '#0e6e21', '#10841d', '#129919', '#15af15']
acmap = ListedColormap(acolors, name="acmap")
acmapr = acmap.reversed()


def assign_xg(data):
  df_match = data.copy()

  #Filtering Data
  df_match = df_match[['Team','Act Name','Action', 'Min', 'Sub 1', 'Sub 2', 'Sub 3', 'Sub 4', 'GW', 'X', 'Y']]
  df_match = df_match[(df_match['Action']=='shoot on target') | (df_match['Action']=='shoot off target') | (df_match['Action']=='shoot blocked') | (df_match['Action']=='goal') | (df_match['Action']=='penalty goal') | (df_match['Action']=='penalty missed')]
  df_match = df_match.reset_index()
  df_match = df_match.sort_values(by=['index'], ascending=False)

  #Cleaning Data
  shots = df_match.copy()
  shots['Mins'] = shots['Min']
  shots['Mins'] = shots['Mins'].astype(float)
  shots = shots[shots['X'].notna()]

  data = shots[['Act Name', 'Team', 'Action', 'Mins', 'Sub 1', 'Sub 2', 'Sub 3', 'Sub 4', 'X', 'Y']]
  data.loc[(data['Action'].str.contains('penalty goal')), 'Sub 3'] = 'Penalty'
  data.loc[(data['Action'].str.contains('penalty goal')), 'Sub 1'] = 'Right Foot'
  data.loc[(data['Action'].str.contains('penalty missed')), 'Sub 3'] = 'Penalty'
  data.loc[(data['Action'].str.contains('penalty missed')), 'Sub 2'] = 'Right Foot'
  data.loc[(data['Action'].str.contains('penalty')), 'X'] = 90
  data.loc[(data['Action'].str.contains('penalty')), 'Y'] = 50
  data.loc[(data['Action'].str.contains('penalty missed')) & ((data['Sub 1'].str.contains('Saved')) | (data['Sub 1'].str.contains('Cleared'))), 'Action'] = 'shoot on target'

  data['Action'] = data['Action'].replace(['shoot on target','shoot off target','shoot blocked','goal','penalty goal','penalty missed'],
                                        ['Shot On','Shot Off','Shot Blocked','Goal','Goal','Shot Off'])
  dft = data.groupby('Action', as_index=False)
  temp = pd.DataFrame(columns = ['Player', 'Team','Event','Mins',
                                 'Shot Type','Situation','X','Y'])
  if (('Goal' in data['Action'].unique()) == True):
    df1 = dft.get_group('Goal')
    df1f = df1[['Act Name', 'Team', 'Action', 'Mins', 'Sub 1', 'Sub 3', 'X', 'Y']]
    df1f.rename(columns = {'Action':'Event', 'Sub 1':'Shot Type', 'Sub 3':'Situation', 'Act Name':'Player'}, inplace = True)
  else:
    df1f = temp.copy()

  if (('Shot On' in data['Action'].unique()) == True):
    df2 = dft.get_group('Shot On')
    df2f = df2[['Act Name','Team', 'Action', 'Mins', 'Sub 2', 'Sub 3', 'X', 'Y']]
    df2f.rename(columns = {'Action':'Event', 'Sub 2':'Shot Type', 'Sub 3':'Situation', 'Act Name':'Player'}, inplace = True)
  else:
    df2f = temp.copy()

  if (('Shot Off' in data['Action'].unique()) == True):
    df3 = dft.get_group('Shot Off')
    df3f = df3[['Act Name','Team', 'Action', 'Mins', 'Sub 3', 'Sub 4', 'X', 'Y']]
    df3f.rename(columns = {'Action':'Event', 'Sub 3':'Shot Type', 'Sub 4':'Situation', 'Act Name':'Player'}, inplace = True)
  else:
    df3f = temp.copy()

  if (('Shot Blocked' in data['Action'].unique()) == True):
    df4 = dft.get_group('Shot Blocked')
    df4f = df4[['Act Name','Team', 'Action', 'Mins', 'Sub 2', 'Sub 3', 'X', 'Y']]
    df4f.rename(columns = {'Action':'Event', 'Sub 2':'Shot Type', 'Sub 3':'Situation', 'Act Name':'Player'}, inplace = True)
  else:
    df4f = temp.copy()

  sa = pd.concat([df1f, df2f, df3f, df4f])
  sa = sa.dropna()
  sa.loc[(sa['Situation'].str.contains('Open play')), 'Situation'] = 'Open Play'
  sa.loc[(sa['Situation'].str.contains('Freekick')), 'Situation'] = 'Set-Piece Free Kick'
  sa.loc[(sa['Shot Type'].str.contains('Header')), 'Shot Type'] = 'Head'

  df_co = sa.sort_values(by=['Mins'], ascending=False)
  df_co['x'] = 100-df_co['X']
  df_co['y'] = df_co['Y']
  df_co['c'] = abs(df_co['Y']-50)

  x=df_co['x']*1.05
  y=df_co['c']*0.68

  df_co['X2']=(100-df_co['X'])*1.05
  df_co['Y2']=df_co['Y']*0.68

  df_co['Distance'] = np.sqrt(x**2 + y**2)
  c=7.32
  a=np.sqrt((y-7.32/2)**2 + x**2)
  b=np.sqrt((y+7.32/2)**2 + x**2)
  k = (c**2-a**2-b**2)/(-2*a*b)
  gamma = np.arccos(k)
  if gamma.size<0:
    gamma = np.pi + gamma
  df_co['Angle Rad'] = gamma
  df_co['Angle Degrees'] = gamma*180/np.pi

  def wasitgoal(row):
    if row['Event'] == 'Goal':
      return 1
    else:
      return 0
  df_co['goal'] = df_co.apply(lambda row: wasitgoal(row), axis=1)

  df_co = df_co.sort_values(by=['Mins'])
  df_co = df_co.reset_index()
  shotdata = df_co[['Player','Team','Event','Mins','Shot Type','Situation','X2','Y2','Distance','Angle Rad','Angle Degrees','goal']]

  shots = shotdata.dropna()
  shots.rename(columns = {'Player':'player', 'Event':'event', 'Mins':'mins', 'Shot Type':'shottype',
                          'Situation':'situation','X2':'X','Y2':'Y', 'Distance':'distance',
                          'Angle Rad':'anglerad','Angle Degrees':'angledeg'}, inplace = True)

  body_part_list=[]
  for index, rows in shots.iterrows():
      if (rows['shottype']=='Right Foot') or (rows['shottype']=='Left Foot'):
          body_part_list.append('Foot')
      elif (rows['shottype']=='Head'):
          body_part_list.append('Head')
      else:
          body_part_list.append('Head')

  shots['body_part']=body_part_list

  shots=shots[shots.body_part != 'Other']
  shots=shots.sort_values(by=['mins'])
  shots.loc[(shots['situation'].str.contains('Set')), 'situation'] = 'Indirect'
  shots.loc[(shots['situation'].str.contains('Corner')), 'situation'] = 'Indirect'
  shots.loc[(shots['situation'].str.contains('Throw')), 'situation'] = 'Open Play'
  shots.loc[(shots['situation'].str.contains('Counter')), 'situation'] = 'Open Play'
  dfxg = shots[['distance', 'angledeg', 'body_part', 'situation', 'goal']]

  #Assign numerical value to body part and situation
  label_encoder = preprocessing.LabelEncoder()
  label_encoder.fit(dfxg["body_part"])
  dfxg['body_part_num'] = label_encoder.transform(dfxg["body_part"])

  label_encoder = preprocessing.LabelEncoder()
  label_encoder.fit(dfxg["situation"])
  dfxg['situation_num'] = label_encoder.transform(dfxg["situation"])

  #assigning xG
  xG=dfxg.apply(calculate_xG, axis=1)
  dfxg = dfxg.assign(xG=xG)
  dfxg['xG'] = dfxg.apply(lambda row: xgfix(row), axis=1)

  fixdata = df_co[['Player', 'Team', 'Event', 'Mins', 'X', 'Y']]
  fixdata['xG'] = dfxg['xG']

  return fixdata

def get_PNdata(tl, rp, min_min, max_min, team, min_pass):
  df = tl.copy()
  df2 = rp.copy()

  pos = df2[df2['Team']==team]
  pos = pos[['Name', 'Position (in match)']]
  pos = pos[pos['Position (in match)'].notna()]
  pos.rename({'Name':'Passer', 'Position (in match)':'Pos'}, axis='columns',inplace=True)

  df['Mins'] = df['Min'].str.split('+').str[0]
  df['Mins'].fillna(df['Min'], inplace=True)
  df['Mins'] = df['Mins'].astype(float)

  firstsub = df[(df['Action']=='subs') | (df['Action']=='red card')]
  firstsub = firstsub[firstsub['Team']==team]
  defmin = min(firstsub['Mins'])
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
  avgpos['Y'] = avgpos['Y'].replace({'A':np.random.randint(2, 20),'B':np.random.randint(21, 40),
                                    'C':np.random.randint(41, 60),
                                    'D':np.random.randint(61, 80),'E':np.random.randint(81, 98)})
  avgpos['X'] = avgpos['X'].replace({'1':np.random.randint(2, 16),'2':np.random.randint(17, 33),
                                    '3':np.random.randint(34, 49),'4':np.random.randint(50, 66),
                                    '5':np.random.randint(67, 83),'6':np.random.randint(84, 98)})
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

  pass_between = pass_between[pass_between['Count']>min_pass]
  pass_between['width'] = (pass_between['Count']/max(pass_between['Count']))*18

  pass_between = pd.merge(pass_between, passtot, on='Passer', how='left')

  return pass_between, defmin
  

def plot_PN(data, min_pass, team, min_min, max_min, match):
  pass_between = data.copy()
  fig, ax = plt.subplots(figsize=(20, 20), dpi=500)
  fig.patch.set_facecolor('#062d2d')
  ax.set_facecolor('#062d2d')

  pitch = Pitch(pitch_type='wyscout', pitch_color='#062d2d', line_color='#fcf8f7',
                corner_arcs=True, stripe=True, stripe_color='#042b2b', goal_type='box', linewidth=3.5)
  pitch.draw(ax=ax)

  cmap = plt.cm.get_cmap(acmap)
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
  avgpos = pass_between[['Passer', 'X', 'Y', 'size', 'Pos']]
  avgpos = avgpos.groupby(['Passer', 'X', 'Y', 'size', 'Pos'], as_index=False).nunique()
      
  pass_nodes = pitch.scatter(avgpos['X'], avgpos['Y'], s = avgpos['size'], zorder=10,
                             color='#f2ff00', edgecolors='#062d2d', linewidth=3, ax=ax)
  
  for index, row in avgpos.iterrows():
    pitch.annotate(row.Pos, xy=(row.X, row.Y), c='#062d2d', va='center', zorder=11,
                   ha='center', size=12, weight='bold', ax=ax, path_effects=path_eff)
  if (min_min == 0):
    min_mins = min_min+1
  else:
    min_mins = min_min

  ax.text(0, -8, 'PASSING NETWORK', ha='left', fontproperties=bold, color='#FFFFFF', size='22', va='center')
  ax.text(0, -4, team.upper()+' | MINUTES: '+str(min_mins)+'-'+str(max_min), ha='left', fontproperties=reg, color='#FFFFFF', size='18', va='center')
  ax.text(100, -4, match.upper(), ha='right', fontproperties=reg, color='#FFFFFF', size='18', va='center')
  
  plt.savefig('/app/lb-matchreport/data/pnet.jpg', dpi=500, bbox_inches='tight')
  
  return fig