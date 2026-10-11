from __future__ import annotations
import copy
import hashlib
import unittest
from toolbox.mod_manager import ModCatalog
from tools.prepare_lc2_public_catalog import PublicCatalogError, public_catalog_from_payload, render_catalog

def spec(path,content):
    return {'path':path,'size_bytes':len(content),'sha256':hashlib.sha256(content).hexdigest().upper()}

def payload():
    current=spec('feature.dll',b'current')
    return {'schema_version':2,'entries':[{
        'id':'public-history-fixture',
        'display':{'name':'Fixture','version':'3.0','author':'Fixture','summary':'Fixture'},
        'operation':{'kind':'bepinex_plugin','expected_filename':'feature.dll','bundled':True,'bundle_dir':'community_mods/fixture','files':[current],
                     'superseded_files':[spec('legacy/feature.dll',b'old one'),spec('LEGACY\\FEATURE.dll',b'old two')]},
        'integrity_policy':{'sha256':current['sha256'],'size_bytes':current['size_bytes'],'version_note':'fixture','author_source':'fixture','author_channel':'local','signature_status':'not_assessed','risk_level':'high','capabilities':['fixture'],'redistribution_status':'test_only'}
    }]}

class PublicHistoryTests(unittest.TestCase):
    def test_distinct_same_path_histories_survive_public_generation_and_consumer(self):
        source=payload()
        frozen=copy.deepcopy(source)
        public=public_catalog_from_payload(source)
        self.assertEqual(source,frozen)
        operation=public['entries'][0]['operation']
        self.assertFalse(operation['bundled'])
        self.assertNotIn('bundle_dir',operation)
        self.assertEqual(operation['superseded_files'],source['entries'][0]['operation']['superseded_files'])
        self.assertEqual(len(ModCatalog.from_payload(public).entries[0].operation.superseded_files),2)
        self.assertEqual(render_catalog(public),render_catalog(public_catalog_from_payload(source)))

    def test_duplicate_current_path_remains_rejected(self):
        source=payload()
        source['entries'][0]['operation']['files'].append(spec('FEATURE.dll',b'another current'))
        with self.assertRaises(PublicCatalogError): public_catalog_from_payload(source)

    def test_duplicate_history_identity_and_inconsistent_size_rejected(self):
        for delta in [0,1]:
            with self.subTest(size_delta=delta):
                source=payload()
                history=source['entries'][0]['operation']['superseded_files']
                duplicate=dict(history[0],path='LEGACY\\FEATURE.dll',sha256=history[0]['sha256'].lower())
                duplicate['size_bytes']+=delta
                history.append(duplicate)
                with self.assertRaises(PublicCatalogError): public_catalog_from_payload(source)

    def test_unsafe_or_invalid_history_remains_rejected(self):
        for field,value in [('path','../feature.dll'),('path','C:/feature.dll'),('path','a//feature.dll'),('path','a/../feature.dll'),('size_bytes',True),('size_bytes',0),('size_bytes',-1),('size_bytes','12'),('sha256','wrong')]:
            with self.subTest(field=field,value=value):
                source=payload()
                source['entries'][0]['operation']['superseded_files'][0][field]=value
                with self.assertRaises(PublicCatalogError): public_catalog_from_payload(source)

if __name__=='__main__': unittest.main()
