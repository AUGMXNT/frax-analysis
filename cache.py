from collections import defaultdict
import httpx
import sqlite3
import sys
import time
from urllib.parse import urlparse


class DB:
  def __init__(self):
    self.con = sqlite3.connect('cache.db')
    self.cur = self.con.cursor()

    sql = '''CREATE TABLE IF NOT EXISTS "cache" (
             "key"	TEXT,
             "value"	TEXT,
             "saved"	INTEGER,
             "expire"	INTEGER,
             PRIMARY KEY("key")
             )
          '''
    self.execute(sql)
  
  def query(self, query, params=()):
    if type(params) == str:
      params = (params,)
    self.cur.execute(query, params)
    return self.cur.fetchall()

  def execute(self, query, params=()):
    if type(params) == str:
      params = (params,)
    self.cur.execute(query, params)
    self.con.commit()


class Cache:
  def __init__(self):
    self.db = DB()

  def get(self, url, refresh=False):
    result = {}
    # Get cached version (yes, even if refresh requested)
    r = self.db.query('SELECT * FROM cache WHERE key = ? ORDER BY saved DESC LIMIT 1', url)

    if r and not refresh:
      result['status'] = 'cached'
      result['key'] = r[0][0]
      result['value'] = r[0][1]
      result['saved'] = r[0][2]
    else:
      # Get
      req = httpx.get(url)
      t = int(time.time())

      retry_count = 1
      # Try a few more times if not 200...
      if req.status_code != 200:
        while req.status_code != 200 and retry_count < 10:
          print('Got response status %s when requesting %s. Sleeping for %s seconds....' % (req.status_code, url, 10 * retry_count))
          time.sleep(10 * retry_count)
          req = httpx.get(url)
          t = int(time.time())
          retry_count += 1

      if req.status_code == 200:
        sql = '''REPLACE INTO cache
                 (key, value, saved)
                 VALUES
                 (?, ?, ?)
              '''
        params = (url, req.content, t)
        self.db.execute(sql, params)

        result['status'] = 'cached'
        result['key'] = url
        result['value'] = req.content
        result['saved'] = t
      else:
          if r:
              result['status'] = 'stale'
              result['key'] = r[0][0]
              result['value'] = r[0][1]
              result['saved'] = r[0][2]
          else:
              result['status'] = 'error'
              result['status_code'] = req.status_code

    return result


### Make cache available as a singleton
cache = Cache()
