import sys, unittest, datetime as dt, json, tempfile, pathlib
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]))
import cloud

class CloudTests(unittest.TestCase):
    def test_register_hash(self):
        p,r=cloud.checked_register()
        self.assertEqual(p['partido_id'],'WORLDS2026-FINAL-GEN-BLG')
        self.assertEqual(r['hash_prediccion'],cloud.digest(p))
    def test_event_idempotency(self):
        p,_=cloud.checked_register()
        now=dt.datetime(2026,11,12,tzinfo=dt.timezone.utc)
        event={'id':1711021,'status':'not_started','number_of_games':5,'scheduled_at':'2026-11-14T19:00:00Z',
            'league':{'name':'Worlds'},'opponents':[{'opponent':{'id':1566,'name':'Bilibili Gaming'}},{'opponent':{'id':2882,'name':'Gen.G'}}]}
        rows=cloud.annotate(cloud.normalize([event],now),p)
        self.assertEqual(rows[0]['estado'],'YA REGISTRADO · B3/C18')
    def test_unknown_team_blocks(self):
        p,_=cloud.checked_register()
        now=dt.datetime(2026,11,12,tzinfo=dt.timezone.utc)
        event={'id':8,'status':'not_started','number_of_games':3,'scheduled_at':'2026-11-14T19:00:00Z','league':{'name':'LCK'},'opponents':[{'opponent':{'id':88,'name':'Test'}},{'opponent':{'id':99,'name':'Test2'}}]}
        rows=cloud.annotate(cloud.normalize([event],now),p)
        self.assertTrue(rows[0]['estado'].startswith('SIN PRONÓSTICO'))
    def test_cannot_leak_token_in_render(self):
        p,r=cloud.checked_register()
        out=cloud.render([],p,r,dt.datetime.now(dt.timezone.utc),'TEST')
        self.assertNotIn('PANDASCORE_TOKEN',out)
        self.assertIn('63.724',out)
    def test_offline_build(self):
        event={'id':1711021,'status':'not_started','number_of_games':5,'scheduled_at':'2026-11-14T19:00:00Z','league':{'name':'Worlds'},'opponents':[{'opponent':{'id':1566,'name':'Bilibili Gaming'}},{'opponent':{'id':2882,'name':'Gen.G'}}]}
        with tempfile.TemporaryDirectory() as t:
            d=pathlib.Path(t)
            (d/'fixture.json').write_text(json.dumps([event]),encoding='utf8')
            status=cloud.build('offline',d/'site',d/'fixture.json',dt.datetime(2026,11,12,tzinfo=dt.timezone.utc))
            self.assertEqual(status['n_eventos'],1)
            self.assertEqual(status['predicciones_nuevas'],0)
            self.assertIn('YA REGISTRADO',(d/'site/index.html').read_text(encoding='utf8'))
    def test_missing_token_fails(self):
        with self.assertRaisesRegex(RuntimeError,'PANDASCORE_TOKEN'):cloud.get_fixtures('')

if __name__=='__main__':unittest.main()
