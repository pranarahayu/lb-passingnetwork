import sys
import pandas as pd
import numpy as np
import streamlit as st
from tempfile import NamedTemporaryFile
import urllib

from mplsoccer import Pitch, VerticalPitch, PyPizza, FontManager
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import matplotlib.patches as patches
from matplotlib.offsetbox import (OffsetImage, AnnotationBbox)
import matplotlib.font_manager as fm
from matplotlib.patches import FancyBboxPatch

import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn import preprocessing

st.set_page_config(page_title='Lapangbola xG Dashboard', layout='wide')
st.header('Assign xG value to shots')
st.markdown('Created by: Prana - R&D Division Lapangbola.com')

sys.path.append("xgmodel.py")
import xgmodel
from xgmodel import calculate_xG
from xgmodel import xgfix

sys.path.append("listfungsi.py")
import listfungsi
from listfungsi import assign_xg
from listfungsi import get_PNdata
from listfungsi import plot_PN

with st.expander("BACA INI DULU."):
    st.write("Aplikasinya kelihatan error karena kedua file yang diperlukan belum diupload, upload dulu. Untuk file timeline, pastikan tambahkan kolom X, Y, dan GW dulu. Format excelnya gak usah ada yang diganti, ya. Untuk file report excelnya, langsung upload aja, gak ada yang perlu diubah.")

tab1, tab2 = st.tabs(['**Shot Map**', '**Passing Network**'])

with tab1:
    tab1.subheader('Generate Shot Map')
    col1, col2 = st.columns(2)
    with col1:
        tl_data = st.file_uploader("Upload file timeline excel!")
        try:
            df_t = pd.read_excel(tl_data, skiprows=[0])
        except ValueError:
            st.error("Please upload the timeline file")

    with col2:
        m_data = st.file_uploader("Upload file report excel!")
        try:
            df_m = pd.read_excel(m_data, skiprows=[0])
            team1 = df_m['Team'][0]
            team2 = df_m['Opponent'][0]
            df_m2 = df_m[['Name']]
        except ValueError:
            st.error("Please upload the excel report file")

    colx, coly = st.columns(2)
    with colx:
        filter = st.selectbox('Select Team', [team1, team2])
    github_url = 'https://github.com/google/fonts/blob/main/ofl/poppins/Poppins-Bold.ttf'
    url = github_url + '?raw=true'

    response = urllib.request.urlopen(url)
    f = NamedTemporaryFile(delete=False, suffix='.ttf')
    f.write(response.read())
    f.close()

    bold = fm.FontProperties(fname=f.name)
    path_eff = [path_effects.Stroke(linewidth=2, foreground='#ffffff'),
                path_effects.Normal()]

    fixdata = assignxg(df_t)

    tempdata = fixdata[['Player', 'Team', 'xG']]
    tempdata = tempdata.groupby(['Player', 'Team'], as_index=False).sum()
    tempdata = tempdata.rename(columns={'Player':'Name'})

    findata = pd.merge(df_m2,tempdata,on='Name',how='left')
    findata['xG'].fillna(0, inplace=True)
    findata['xG'] = round(findata['xG'],2)

    with coly:
        df_players = fixdata[fixdata['Team']==filter].reset_index(drop=True)
        pilter = st.selectbox('Select Player', pd.unique(df_players['Player']))
        all_players = st.checkbox('Select All Players')

    @st.cache_data
    def convert_df(df):
        return df.to_csv().encode('utf-8')
    csv = convert_df(findata)

    st.download_button(label='Download Data Excel+xG!',
                       data=csv,
                       file_name='Player+xG_'+team1+'vs'+team2+'.csv',
                       mime='text/csv')
                   
    colm, coln = st.columns(2)

    with colm:
        arah_shot = st.checkbox('Include arah shot?')
        disp = fixdata[fixdata['Team']==filter]
        if all_players:
            st.write(disp)
        else:
            st.write(disp[disp['Player']==pilter])

    with coln:
        #Attempts Map
        fig, ax = plt.subplots(figsize=(20, 20), dpi=500)
        pitch = VerticalPitch(half=True, pitch_type='wyscout', corner_arcs=True,
                              pitch_color='#ffffff', line_color='#000000',
                              stripe_color='#fcf8f7', goal_type='box', pad_bottom=5,
                              pad_right=0.5, pad_left=0.5, stripe=True, linewidth=3.5)
        pitch.draw(ax=ax)

        df_team = fixdata[fixdata['Team'] == filter].reset_index(drop=True)
        goal = df_team[df_team['Event']=='Goal']['Event'].count()
        son = df_team[df_team['Event']=='Shot On']['Event'].count()
        soff = df_team[df_team['Event']=='Shot Off']['Event'].count()
        sblocked = df_team[df_team['Event']=='Shot Blocked']['Event'].count()
        xgtot = round((df_team['xG'].sum()),2)

        df_player = df_players[df_players['Player'] == pilter].reset_index(drop=True)
        goalp = df_player[df_player['Event']=='Goal']['Event'].count()
        shots = df_player[df_player['Event']!='Goal']['Event'].count() + goalp
        xgtotp = round((df_player['xG'].sum()),2)
        gps = round((goalp/shots)*100,1)
        xgps = round((xgtotp/shots),2)

        if all_players:
            if arah_shot:
                for i in range(len(df_team)):
                if (df_team['Event'][i] == 'Goal' or df_team['Event'][i] == 'Penalty Goal'):
                    ax.scatter(df_team['Y'][i], df_team['X'][i], s=df_team['xG'][i]*10000,
                               c='#7ed957', marker='o', edgecolors='#000000', lw=3.5, zorder=10)
                    pitch.arrows(df_team['X'][i], df_team['Y'][i],df_team['X2'][i], df_team['Y2'][i],
                                 width=4, headwidth=8, headlength=10, color='#7ed957', ax=ax)
                elif (df_team['Event'][i] == 'Shot On'):
                    ax.scatter(df_team['Y'][i], df_team['X'][i], s=df_team['xG'][i]*10000,
                               c='#f2ff00', marker='o', edgecolors='#000000', lw=3.5, zorder=10)
                    pitch.arrows(df_team['X'][i], df_team['Y'][i],df_team['X2'][i], df_team['Y2'][i],
                                 width=4, headwidth=8, headlength=10, color='#f2ff00', ax=ax)
                elif (df_team['Event'][i] == 'Shot Off'):
                    ax.scatter(df_team['Y'][i], df_team['X'][i], s=df_team['xG'][i]*10000,
                               c='#a6a6a6', marker='o', edgecolors='#000000', lw=3.5, zorder=10)
                    pitch.arrows(df_team['X'][i], df_team['Y'][i],df_team['X2'][i], df_team['Y2'][i],
                                 width=4, headwidth=8, headlength=10, color='#a6a6a6', ax=ax)
                else:
                    ax.scatter(df_team['Y'][i], df_team['X'][i], s=df_team['xG'][i]*10000,
                               c='#e66009', marker='o', edgecolors='#000000', lw=3.5, zorder=10)
            else:
                for i in range(len(df_team)):
                if (df_team['Event'][i] == 'Goal' or df_team['Event'][i] == 'Penalty Goal'):
                    ax.scatter(df_team['Y'][i], df_team['X'][i], s=df_team['xG'][i]*10000,
                               c='#7ed957', marker='o', edgecolors='#000000', lw=3.5)
                elif (df_team['Event'][i] == 'Shot On'):
                    ax.scatter(df_team['Y'][i], df_team['X'][i], s=df_team['xG'][i]*10000,
                               c='#f2ff00', marker='o', edgecolors='#000000', lw=3.5)
                elif (df_team['Event'][i] == 'Shot Off'):
                    ax.scatter(df_team['Y'][i], df_team['X'][i], s=df_team['xG'][i]*10000,
                               c='#a6a6a6', marker='o', edgecolors='#000000', lw=3.5)
                else:
                    ax.scatter(df_team['Y'][i], df_team['X'][i], s=df_team['xG'][i]*10000,
                               c='#e66009', marker='o', edgecolors='#000000', lw=3.5)

            annot_texts = ['Goals', 'Shots\nOn Target', 'Shots\nOff Target', 'Shots\nBlocked', 'xG Total']
            annot_x = [10.83 + x*17.83 for x in range(0,5)]
            annot_stats = [goal, son, soff, sblocked, xgtot]

            for x, s, h in zip(annot_x, annot_texts, annot_stats):
                #ax.add_patch(FancyBboxPatch((x, 62), 7, 3.5, fc='#ffffff', ec='#ffffff', lw=2))
                ax.annotate(text=s, size=22, xy=(x+3.5, 56.5), xytext=(0,-18),
                            textcoords='offset points', color='black', ha='center',
                            zorder=9, va='center', fontproperties=bold, path_effects=path_eff)
                ax.annotate(text=h, size=78, xy=(x+3.5, 60), xytext=(0,-18),
                            textcoords='offset points', color='black', ha='center',
                            zorder=9, va='center', fontproperties=bold, path_effects=path_eff)

            ax.add_patch(FancyBboxPatch((0, 45), 200, 4.5, fc='#ffffff', ec='#ffffff', lw=2))

            annot_x = [4 + x*25 for x in range(0,4)]
            annot_texts = ['Goals', 'Shots On Target', 'Shots Off Target', 'Shots Blocked']

            ax.scatter(4, 48, s=800, c='#7ed957', lw=3.5,
                       marker='o', edgecolors='#000000')
            ax.scatter(29, 48, s=800, c='#f2ff00', lw=3.5,
                       marker='o', edgecolors='#000000')
            ax.scatter(54, 48, s=800, c='#a6a6a6', lw=3.5,
                       marker='o', edgecolors='#000000')
            ax.scatter(79, 48, s=800, c='#e66009', lw=3.5,
                       marker='o', edgecolors='#000000')

            for x, s in zip(annot_x, annot_texts):
                ax.annotate(text=s, size=24, xy=(x+2.5, 49), xytext=(0,-18),
                            textcoords='offset points', color='black', ha='left',
                            zorder=9, va='center', fontproperties=bold)

            ax.add_patch(FancyBboxPatch((0.65, 50.5), 35, 1.35, fc='#cbfd06', ec='#cbfd06', lw=2))
            ax.annotate(text=filter, size=26, xy=(1, 52), xytext=(0,-18),
                        textcoords='offset points', color='black', ha='left',
                        zorder=9, va='center', fontproperties=bold)

            ax.annotate(text='-Nilai xG->', size=21, xy=(87, 54), xytext=(0,-18),
                        textcoords='offset points', color='black', ha='left',
                        zorder=9, va='center', fontproperties=bold, path_effects=path_eff)
            ax.scatter(87.5, 51.15, s=300, c='#a6a6a6', lw=2,
                       marker='o', edgecolors='#000000')
            ax.scatter(90.5, 51.25, s=500, c='#a6a6a6', lw=2,
                       marker='o', edgecolors='#000000')
            ax.scatter(93.5, 51.35, s=700, c='#a6a6a6', lw=2,
                       marker='o', edgecolors='#000000')
            ax.scatter(97, 51.45, s=900, c='#a6a6a6', lw=2,
                       marker='o', edgecolors='#000000')
            fig.savefig('smap.jpg', dpi=500, bbox_inches='tight')
            st.pyplot(fig)
    
        else:
            for i in range(len(df_player)):
            if (df_player['Event'][i] == 'Goal' or df_player['Event'][i] == 'Penalty Goal'):
                ax.scatter(df_player['Y'][i], df_player['X'][i], s=df_player['xG'][i]*10000,
                           c='#7ed957', marker='o', edgecolors='#000000', lw=3.5)
            elif (df_player['Event'][i] == 'Shot On'):
                ax.scatter(df_player['Y'][i], df_player['X'][i], s=df_player['xG'][i]*10000,
                           c='#f2ff00', marker='o', edgecolors='#000000', lw=3.5)
            elif (df_player['Event'][i] == 'Shot Off'):
                ax.scatter(df_player['Y'][i], df_player['X'][i], s=df_player['xG'][i]*10000,
                           c='#a6a6a6', marker='o', edgecolors='#000000', lw=3.5)
            else:
                ax.scatter(df_player['Y'][i], df_player['X'][i], s=df_player['xG'][i]*10000,
                           c='#e66009', marker='o', edgecolors='#000000', lw=3.5)

            annot_texts = ['Goals', 'xG', 'Shots', 'Conversion\nRatio (%)', 'xG/Shots']
            annot_x = [10.83 + x*17.83 for x in range(0,5)]
            annot_stats = [goalp, xgtotp, shots, gps, xgps]

            for x, s, h in zip(annot_x, annot_texts, annot_stats):
            #ax.add_patch(FancyBboxPatch((x, 62), 7, 3.5, fc='#ffffff', ec='#ffffff', lw=2))
                ax.annotate(text=s, size=22, xy=(x+3.5, 56.5), xytext=(0,-18),
                            textcoords='offset points', color='black', ha='center',
                            zorder=9, va='center', fontproperties=bold, path_effects=path_eff)
                ax.annotate(text=h, size=78, xy=(x+3.5, 60), xytext=(0,-18),
                            textcoords='offset points', color='black', ha='center',
                            zorder=9, va='center', fontproperties=bold, path_effects=path_eff)

            ax.add_patch(FancyBboxPatch((0, 45), 200, 4.5, fc='#ffffff', ec='#ffffff', lw=2))

            annot_x = [4 + x*25 for x in range(0,4)]
            annot_texts = ['Goals', 'Shots On Target', 'Shots Off Target', 'Shots Blocked']

            ax.scatter(4, 48, s=800, c='#7ed957', lw=3.5,
                       marker='o', edgecolors='#000000')
            ax.scatter(29, 48, s=800, c='#f2ff00', lw=3.5,
                       marker='o', edgecolors='#000000')
            ax.scatter(54, 48, s=800, c='#a6a6a6', lw=3.5,
                       marker='o', edgecolors='#000000')
            ax.scatter(79, 48, s=800, c='#e66009', lw=3.5,
                       marker='o', edgecolors='#000000')

            for x, s in zip(annot_x, annot_texts):
                ax.annotate(text=s, size=24, xy=(x+2.5, 49), xytext=(0,-18),
                            textcoords='offset points', color='black', ha='left',
                            zorder=9, va='center', fontproperties=bold)

            ax.add_patch(FancyBboxPatch((0.65, 50.5), 45, 1.35, fc='#cbfd06', ec='#cbfd06', lw=2))
            ax.annotate(text=pilter, size=26, xy=(1, 52), xytext=(0,-18),
                        textcoords='offset points', color='black', ha='left',
                        zorder=9, va='center', fontproperties=bold)

            ax.annotate(text='-Nilai xG->', size=21, xy=(87, 54), xytext=(0,-18),
                        textcoords='offset points', color='black', ha='left',
                        zorder=9, va='center', fontproperties=bold, path_effects=path_eff)
            ax.scatter(87.5, 51.15, s=300, c='#a6a6a6', lw=2,
                       marker='o', edgecolors='#000000')
            ax.scatter(90.5, 51.25, s=500, c='#a6a6a6', lw=2,
                       marker='o', edgecolors='#000000')
            ax.scatter(93.5, 51.35, s=700, c='#a6a6a6', lw=2,
                       marker='o', edgecolors='#000000')
            ax.scatter(97, 51.45, s=900, c='#a6a6a6', lw=2,
                       marker='o', edgecolors='#000000')
            fig.savefig('smap.jpg', dpi=500, bbox_inches='tight')
            st.pyplot(fig)
    
        with open('smap.jpg', 'rb') as img:
            fn = 'AttemptsMap_'+filter+'.jpg'
            btn = st.download_button(label="Download Attempts Map!", data=img,
                                     file_name=fn, mime="image/jpg")

with tab2:
    try:
        tab2.subheader('Generate Passing Network')
        col1, col2 = st.columns(2)
        with col1:
            tl_data = st.file_uploader("Upload file timeline excel!")
            tl = pd.read_excel(tl_data, skiprows=[0])

        with col2:
            rp_data = st.file_uploader("Upload file report excel!")
            rp = pd.read_excel(rp_data, skiprows=[0])
            team1 = df_m['Team'][0]
            team2 = df_m['Opponent'][0]
            match = team1 +' vs '+team2
            
        colx, coly, colz = st.columns(3)
        with colx:
            filter = st.selectbox('Select Team', [team1, team2])
        with coly:
            min_pass = st.number_input('Select Min. Successful Passes',
                                       min_value=0, max_value=3, step=1)
        with colz:
            menit = st.slider('Select Minutes',
                              0, 90, (1, 30))
        
        plotdata = get_PNdata(tl, rp, menit[0], menit[1], filter, min_pass)
        pass_between = plotdata[0]
        
        if 'clicked' not in st.session_state:
            st.session_state.clicked = False
        
        def click_button():
            st.session_state.clicked = True
            
        st.button('Rekomenasikan menit!', on_click=click_button)
        if st.session_state.clicked:
            st.write('Untuk tim ini direkomendasikan memilih menit 1 hingga '+plotdata[1])
        
        pn = plot_PN(pass_between, min_pass, filter, menit[0], menit[1], match)
        
        with open('/app/lb-matchreport/data/pnet.jpg', 'rb') as img:
            fn = 'PN_'+filter+'-'+f_team+'.jpg'
            btn = st.download_button(label="Download Passing Network", data=img,
                                     file_name=fn, mime="image/jpg")
        st.pyplot(pn)
        
    except ValueError:
        st.error("Please upload the files")