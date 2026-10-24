import unittest, json, gzip, base64, hashlib, random, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from upload_post_d30_records import encode_record, decode_record, RECORD_ENCODING

class UploadEncodingTests(unittest.TestCase):
    def test_medium_json_exact_bytes(self):
        raw=(json.dumps({'cm':[[100000,0,0,3,0,0]]*2000,'binding':{'commit':'01ec8dee'}},indent=2)+'\n').encode()
        self.assertLess(len(raw),1024*1024)
        encoded=encode_record(raw)
        self.assertLess(len(encoded),len(raw)//10)
        self.assertEqual(decode_record(encoded),raw)
        envelope=json.loads(encoded)
        self.assertEqual(envelope['original_sha256'],hashlib.sha256(raw).hexdigest())
    def test_medium_log_exact_bytes(self):
        raw=('PORTFOLIO_PROGRESS worker step=4000 训练\r\n'*10000).encode()
        self.assertLess(len(raw),1024*1024)
        self.assertEqual(decode_record(encode_record(raw)),raw)
        self.assertEqual(json.loads(encode_record(raw))['record_encoding'],RECORD_ENCODING)
    def test_small_json_stays_readable(self):
        raw=b'{ "count": 7 }\n'
        self.assertEqual(encode_record(raw),raw)
        self.assertEqual(decode_record(raw),raw)
    def test_aggregate_medium_json_regression(self):
        raw=json.dumps({'counts':list(range(20000)),'binding':'source'},indent=2).encode()
        self.assertLess(len(raw),1024*1024)
        old_total=len(raw)*3000
        new_total=len(encode_record(raw))*3000
        self.assertGreater(old_total,512*1024**2)
        self.assertLess(new_total,512*1024**2)
    def test_sha_corruption_rejected(self):
        envelope=json.loads(encode_record(json.dumps({'cm':[1]*10000}).encode()))
        envelope['original_sha256']='0'*64
        with self.assertRaises(ValueError):decode_record(json.dumps(envelope).encode())
    def test_size_corruption_rejected(self):
        envelope=json.loads(encode_record(json.dumps({'cm':[1]*10000}).encode()))
        envelope['original_bytes']+=1
        with self.assertRaises(ValueError):decode_record(json.dumps(envelope).encode())
if __name__=='__main__':unittest.main()
