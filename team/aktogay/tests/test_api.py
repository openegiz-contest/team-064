import json,sys,threading,unittest,urllib.request,urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import app

class APITests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  app.runtime=app.Runtime('standalone');app.runtime.publish()
  cls.server=app.ThreadingHTTPServer(('127.0.0.1',0),app.Handler)
  cls.url=f'http://127.0.0.1:{cls.server.server_port}'
  threading.Thread(target=cls.server.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close()
 def request(self,path,body=None):
  req=urllib.request.Request(self.url+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json'})
  try:
   with urllib.request.urlopen(req) as r:return r.status,json.load(r)
  except urllib.error.HTTPError as e:return e.code,json.load(e)
 def test_controls_end_to_end(self):
  code,_=self.request('/api/control',{'action':'start'});self.assertEqual(code,200)
  self.request('/api/scenario',{'id':'crusher-outage'})
  _,d=self.request('/api/state');self.assertEqual(d['snapshot']['crusher_state'],'fault');self.assertEqual(d['snapshot']['scenario'],'crusher-outage')
  self.request('/api/control',{'action':'pause'})
  code,_=self.request('/api/settings',{'fleet':4,'power_mw':40});self.assertEqual(code,200)
  _,d=self.request('/api/state');self.assertEqual(d['snapshot']['settings']['fleet'],4);self.assertEqual(d['snapshot']['minute'],0);self.assertEqual(d['snapshot']['status'],'ready')
  self.request('/api/reset',{})
 def test_invalid_controls_are_explicit(self):
  for path,body in [('/api/control',{'action':'invent'}),('/api/settings',{'fleet':0}),('/api/settings',[]),('/api/scenario',{'id':'unknown'})]:
   with self.subTest(path=path):self.assertEqual(self.request(path,body)[0],400)
 def test_static_bundle_is_served(self):
  for path,content in [('/','Start Simulation'),('/static/scene.js','WebGLRenderer'),('/static/vendor/three.module.js','WebGLRenderer')]:
   with urllib.request.urlopen(self.url+path) as r:self.assertEqual(r.status,200);self.assertIn(content,r.read().decode())
  self.assertEqual(self.request('/static/%2e%2e/model.py')[0],403)
 def test_health_and_source_are_honest(self):
  _,d=self.request('/healthz');self.assertEqual(d['mode'],'standalone');self.assertFalse(d['mqtt']);self.assertTrue(d['ok'])
 def test_paired_forecast_over_api(self):
  code,_=self.request('/api/compare',{'id':'power-limit'});self.assertEqual(code,200)
  _,d=self.request('/api/state');self.assertEqual(d['snapshot']['comparison']['scenario'],'power-limit')

if __name__=='__main__':unittest.main(verbosity=2)
