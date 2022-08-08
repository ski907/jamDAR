#-------------------------------------------------------------------------------
# Name          JamDAR
# Description:  Tool to identify ice jams from stream gage stage records with a silly name
# Author:       Chandler Engel
#               US Army Corps of Engineers
#               Cold Regions Research and Engineering Laboratory (CRREL)
#               Chandler.S.Engel@usace.army.mil
# Created:      07 August 2022
# Updated:      -
#
#         
#-------------------------------------------------------------------------------

import streamlit as st
import pandas as pd
import numpy as np
import dataretrieval.nwis as nwis
import plotly.express as px

st.title('JamDAR')
form = st.form(key='my-form')
site = form.text_input('Enter USGS Gage ID', value='06052500')
year1 = form.text_input('Start Year', value='2010')
year2 = form.text_input('End Year', value='2022')
years = range(int(year1),int(year2)+1) 
submit = form.form_submit_button('Submit')
st.write('Ex. Gallatin River MT: 06052500') 

@st.cache(suppress_st_warning=True)
def download_iv_data(site,years):
    dfs = []
    
    for year in years:
        dfs.append(nwis.get_record(sites=site, service='iv', start=f'{year-1}-12-01', end=f'{year}-07-01',parameterCd='00065'))
        #print(f'{year} complete')
        st.write(f'{year} complete')
    df = pd.concat(dfs)
    csv = df.to_csv().encode('utf-8')
    return csv
    
@st.cache
def get_site_info(site):
    site_info = nwis.get_record(sites=site, service='site')
    return site_info

site_info = get_site_info(site)
st.write('current site: ',site_info.station_nm[0])



if submit:
    try:
        csv = download_iv_data(site,years)
        st.download_button(
        "Press to Download",
        csv,
        f'{site}_DEC-JUN_{year1}-{year2}.csv',
        "text/csv",
        key='download-csv'
    )
    except:
        st.write("**That ID didn't work, please check the number or try a different one**")

@st.cache
def process_data(df):
    df.index = pd.to_datetime(df.index,utc=True).tz_localize(None)
    df = fill_gaps(df,frequency='15min')
    df['gradient'] = pd.DataFrame(np.gradient(df['00065']),index=df.index)
    #st.write(df)
    return df
    
def fill_gaps(df,frequency='H'):
    #this fills in the gaps between periods with data with zeros, 
    #necessary for smoothing
    idx = pd.date_range(min(df.index), max(df.index), freq=frequency)
    df = df.reindex(idx, fill_value=np.nan)
    return df

def find_outliers(df):
    qlow = df.quantile(1-0.9995)
    qhigh=df.quantile(0.9995)
    outliers = df[((df<qlow) | (df>qhigh))]
    return outliers

def get_candidates(df):
    jamcans = list(np.unique(find_outliers(df.gradient).index.date))
    #jamcans = [date_obj.strftime('%Y%m%d') for date_obj in jamcans]
    jamcans = [date_obj.strftime('%d %b %Y') for date_obj in jamcans]
    return jamcans
    
choice = None
uploaded_file = st.file_uploader("Choose a file")

if uploaded_file is not None:
     df = pd.read_csv(uploaded_file)
     df.index = df.datetime
     
     
     df = process_data(df)
     max_stage = df['00065'].max()
     min_stage = df['00065'].min()
     max_gradient = df.gradient.max()
     min_gradient = df.gradient.min()
     jamcans = get_candidates(df)
     #choice =  st.selectbox('pick one', jamcans)
     choice = st.radio('pick one', jamcans,horizontal=True)
     
if choice is not None:
    st.write(pd.to_datetime(choice).strftime('%d %B, %Y'))
    start_date = (pd.to_datetime(choice)-pd.tseries.offsets.Day(2)).strftime('%Y%m%d')
    end_date = (pd.to_datetime(choice)+pd.tseries.offsets.Day(2)).strftime('%Y%m%d')
    df2 = df.loc[start_date : end_date]
    fig = px.line(df2, x = df2.index, y = '00065',title=f'{site_info.station_nm[0]}')
    fig.update_yaxes(range=[min_stage, max_stage])
    st.write(fig)
    #st.plotly_chart(px.line(df2, x = df2.index, y = '00065'))
    fig2 =px.line(df2, x = df2.index, y = 'gradient')
    fig2.update_yaxes(range=[min_gradient, max_gradient])
    st.write(fig2)

