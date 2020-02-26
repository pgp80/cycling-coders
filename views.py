from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseNotFound
from .forms import UploadFileForm
from .forms import FitFileForm
from PMC.models import Ride
from .models import RideSum
from .models import FitFiles
from django.db import connections
from django.views import generic
from django.conf import settings
import pandas as pd
import numpy as np
from stravalib.client import Client
from stravalib.model import Activity
from stravalib.model import Stream
import datetime 
import time
import json
import sqlite3
from sqlalchemy import create_engine
import io
from fitparse import FitFile
from bokeh.plotting import figure, output_file, show
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.graph_objs as go

def upload(request):
#Form stuff
    if request.method=='POST':
        form=FitFileForm(request.POST, request.FILES)  
        if form.is_valid():
            #form.save() this saves the file to Django model, temporarily disabled
#Processing Fit File using fitparse library
            data=request.FILES['fitfiles'].read()
            fitfile = FitFile(data)
            while True:
                try:
                    fitfile.messages
                    break
                except KeyError:
                    continue

            workout = []
            for record in fitfile.get_messages('record'):
                r = {}
    # Go through all the data entries in this record
                for record_data in record:
                    r[record_data.name] = record_data.value

                workout.append(r)

            df = pd.DataFrame(workout)
            df['time']=(df['timestamp'] - df['timestamp'].iloc[0]).astype('timedelta64[s]')
            #print(df)
            date = df['timestamp'].iloc[0]
#FTP is a manual entry right now        
            ftp = 295

# Normalized Power
            norm_power = np.sqrt(np.sqrt(np.mean(df['power'].rolling(30).mean() ** 4)))

# Intensity
            intensity = norm_power / ftp

            moving_time = len(df)

# Trainings Stress Score
            tss = (moving_time * norm_power * intensity) / (ftp * 3600.0) * 100.0
            fitsumdict = {}
            fitsumdict['ftp']=ftp
            fitsumdict['norm_power']=int(round(norm_power, 1))
            fitsumdict['intensity']=float(round(intensity, 2))
            fitsumdict['tss']=float(round(tss, 1))
            fitsumdict['date']=str(date)
 #saving summary data into Dataframe       
            fitsumdf=pd.DataFrame.from_dict([fitsumdict])
            print(fitsumdf)
 #saving Dataframe to Django model database
            user = settings.DATABASES['default']['USER']
            password = settings.DATABASES['default']['PASSWORD']
            database_name = settings.DATABASES['default']['NAME']

            database_url = 'postgresql://{user}:{password}@localhost:5432/{database_name}'.format(
                user=user,
                password=password,
                database_name=database_name,
            )
            engine = create_engine(database_url, echo=False)
            fitsumdf.to_sql(RideSum._meta.db_table, con=engine, if_exists='append', index=False)
            #return redirect('/rides/')
            #output_file('analyze.html')

#Plotting power data using Plotly Dash
            dash

            trace1=go.Scatter(x=df['time'], y=df['power'])
            fig=go.Figure(data=[trace1])

            external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css']

            analyze = dash.Dash(__name__, external_stylesheets=external_stylesheets)

            analyze.layout = html.Div([
                dcc.Graph(figure=fig),
                fig.show()
            ])
  
  #End of upload function
    else:
        form=FitFileForm()
    return render(request, 'PMC/upload.html', {'form': form})
