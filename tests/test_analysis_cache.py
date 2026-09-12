from track_sprint.analysis_cache import find_cached_analysis
from track_sprint.artifacts import write_json


def test_cache_requires_exact_uploaded_content_and_complete_artifacts(tmp_path):
    p=tmp_path/'saved';p.mkdir()
    write_json(p/'manifest.json',dict(input_sha256='abc',analysis_id='run'))
    write_json(p/'summary.json',dict(video={'sha256':'abc'},analysis_id='run',quality='usable',config={'start':1,'end':2}))
    assert find_cached_analysis(tmp_path,'abc') is None
    for name in ('original.mp4','annotated.mp4','landmarks.npz','series.json','frames'):
        (p/name).touch()
    assert find_cached_analysis(tmp_path,'abc')[0] == p
    assert find_cached_analysis(tmp_path,'another-video') is None
    write_json(p/'summary.json',dict(video={'sha256':'abc'},analysis_id='different',quality='usable',config={}))
    assert find_cached_analysis(tmp_path,'abc') is None
