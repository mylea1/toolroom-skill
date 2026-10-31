import json, tempfile, unittest, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_catalog import discover,apply_annotations,render,remote_url
class CatalogTests(unittest.TestCase):
 def test_discovery_duplicates_and_escape(self):
  with tempfile.TemporaryDirectory() as t:
   root=Path(t)
   for name in ['one','two']:
    p=root/name;p.mkdir();(p/'package.json').write_text(json.dumps({'name':'fixture','version':'1.0','description':'</script><script>alert(1)</script>','scripts':{'dev':'example'}}))
    child=p/'internal';child.mkdir();(child/'package.json').write_text('{}')
   (root/'alias').symlink_to(root/'one',target_is_directory=True)
   ps,cov=discover([root]);self.assertEqual(len(ps),2);self.assertEqual(cov['errors'],[])
   self.assertTrue(any(p['aliases'] for p in ps));self.assertEqual(len(ps[0]['commands']),1)
   groups,flows=apply_annotations(ps,{'workflows':[{'steps':[{'projects':['one']}]}]})
   self.assertEqual(len(groups),1);self.assertEqual(len(flows[0]['steps'][0]['ids']),1)
   out=root/'result.html';render({'projects':ps},out)
   self.assertNotIn('</script><script>alert',out.read_text())
 def test_remote_credentials(self):
  self.assertEqual(remote_url('https://user:secret@github.com/a/b.git?token=secret'),'https://github.com/a/b')
  self.assertEqual(remote_url('git@github.com:a/b.git'),'https://github.com/a/b')
  self.assertEqual(remote_url('javascript:alert(1)'),'')
if __name__=='__main__':unittest.main()
