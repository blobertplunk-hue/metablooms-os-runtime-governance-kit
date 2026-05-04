#!/usr/bin/env python3
from __future__ import annotations
import functools, json, random, time, traceback
from pathlib import Path

def json_stage_log(log_path):
 path=Path(log_path); path.parent.mkdir(parents=True,exist_ok=True)
 def deco(fn):
  @functools.wraps(fn)
  def wrapper(*args,**kwargs):
   st=time.time(); path.open('a',encoding='utf-8').write(json.dumps({'event':'start','function':fn.__name__,'ts':st},sort_keys=True)+'\n')
   try:
    res=fn(*args,**kwargs); path.open('a',encoding='utf-8').write(json.dumps({'event':'end','function':fn.__name__,'elapsed_sec':round(time.time()-st,3),'status':'ok'},sort_keys=True)+'\n'); return res
   except Exception as exc:
    path.open('a',encoding='utf-8').write(json.dumps({'event':'error','function':fn.__name__,'elapsed_sec':round(time.time()-st,3),'error':repr(exc),'traceback':traceback.format_exc()[-4000:]},sort_keys=True)+'\n'); raise
  return wrapper
 return deco

def bounded_retry(attempts=2, wait_sec=0.25, retry_exceptions=(Exception,)):
 if attempts < 1: raise ValueError('attempts must be >=1')
 def deco(fn):
  @functools.wraps(fn)
  def wrapper(*args,**kwargs):
   last=None
   for i in range(attempts):
    try: return fn(*args,**kwargs)
    except retry_exceptions as exc:
     last=exc
     if i<attempts-1: time.sleep(wait_sec)
   raise last
  return wrapper
 return deco

def lock_seed(seed=42):
 def deco(fn):
  @functools.wraps(fn)
  def wrapper(*args,**kwargs):
   random.seed(seed); return fn(*args,**kwargs)
  return wrapper
 return deco

def fail_closed_fallback(mock_data=None, *, allow_mock=False):
 def deco(fn):
  @functools.wraps(fn)
  def wrapper(*args,**kwargs):
   try: return fn(*args,**kwargs)
   except Exception:
    if allow_mock: return mock_data
    raise
  return wrapper
 return deco
