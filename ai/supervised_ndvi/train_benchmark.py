"""Reproduce VanRakshak's real labelled NDVI benchmark.
Dataset: climatechange-ai-tutorials/detect-deforestation/data/amazon_sits_samples.csv
Labels: INPE PRODES 2022. See README for limitations.
"""
import json, math, time
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import precision_recall_fscore_support, confusion_matrix, jaccard_score, accuracy_score

DATA_URL="https://raw.githubusercontent.com/climatechange-ai-tutorials/detect-deforestation/main/data/amazon_sits_samples.csv"
OUT=Path(__file__).with_name("benchmark_model.json")

def block(lon,lat):
    gx=np.floor((lon+180)/0.02).astype(np.int64); gy=np.floor((lat+90)/0.02).astype(np.int64)
    return ((gx*73856093) ^ (gy*19349663)) % 10

def features(df):
    cols=[f"ndvi_{i:02d}" for i in range(24)]
    x=df[cols].to_numpy(float)
    mean=x.mean(1); early=x[:,:4].mean(1); late=x[:,-4:].mean(1)
    slope=np.array([np.polyfit(np.arange(24),r,1)[0] for r in x])
    return np.c_[x,mean,early,late,late-early,x.min(1),x.max(1),x.std(1),slope]

def metrics(y,p):
    tn,fp,fn,tp=confusion_matrix(y,p,labels=[0,1]).ravel()
    pr,re,f1,_=precision_recall_fscore_support(y,p,average="binary",zero_division=0)
    iou=jaccard_score(y,p,average="binary",zero_division=0)
    return {"n":len(y),"tp":int(tp),"tn":int(tn),"fp":int(fp),"fn":int(fn),"precision":pr,"recall":re,"f1":f1,"iou":iou,"dice":f1,"fpr":fp/max(1,fp+tn),"accuracy":accuracy_score(y,p)}

def main():
    df=pd.read_csv(DATA_URL); X=features(df); y=(df.label=="deforested").astype(int).to_numpy()
    s=block(df.lon.to_numpy(),df.lat.to_numpy()); tr=s>=4; va=(s==2)|(s==3); te=s<=1
    mu=X[tr].mean(0); sd=X[tr].std(0); sd[sd==0]=1
    Z=(X-mu)/sd
    m=LogisticRegression(class_weight="balanced",C=1/0.0015,max_iter=5000,solver="lbfgs").fit(Z[tr],y[tr])
    vp=m.predict_proba(Z[va])[:,1]; best=max(np.arange(.15,.86,.01),key=lambda t:metrics(y[va],vp>=t)["f1"])
    start=time.perf_counter(); prob=m.predict_proba(Z[te])[:,1]; pred=prob>=best; elapsed=(time.perf_counter()-start)*1000
    print(json.dumps({"threshold":float(best),"test":metrics(y[te],pred),"inference_ms_total":elapsed},indent=2))

if __name__=="__main__": main()
