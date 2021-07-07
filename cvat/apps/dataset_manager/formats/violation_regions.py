# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

import os
import os.path as osp
import zipfile
import yaml
from collections import OrderedDict
from glob import glob
from tempfile import TemporaryDirectory

from cvat.apps.dataset_manager.bindings import match_dm_item
from cvat.apps.dataset_manager.util import make_zip_archive
from cvat.apps.engine.frame_provider import FrameProvider
from datumaro.components.extractor import DatasetItem

from .registry import exporter, importer


def pairwise(iterable):
    a = iter(iterable)
    return zip(a, a)

def dump_as_site_config(file_object, annotations):

    for frame_annotation in annotations.group_by_frame(include_empty=True):
        frame_id = frame_annotation.frame
        file_object.write(str.encode(str(frame_id) + ":\n"))
        for shape in frame_annotation.labeled_shapes:

            pts = ('],['.join((','.join((
                            "{:.2f}".format(x),
                            "{:.2f}".format(y)
                        )) for x, y in pairwise(shape.points))
                    ))

            line = "  " + shape.label + ": [["+ pts +"]]\n"
            file_object.write(str.encode(line))

def load(file_object, annotations):

    site_config = yaml.safe_load(file_object)

    for k,v in site_config[0].items():
        shape = {}
        shape['attributes'] = []
        shape['frame'] = 0
        shape['label'] = k
        shape['group'] = 0
        shape['source'] = 'manual'

        shape['type'] = 'polygon'
        shape['occluded'] = 0
        shape['z_order'] = 0

        shape['points'] = []
        for p in v:
            shape['points'].extend(map(float, p))
        annotations.add_shape(annotations.LabeledShape(**shape))



def _export(dst_file, task_data, anno_callback, save_images=False):
    with TemporaryDirectory() as temp_dir:
        with open(osp.join(temp_dir, 'site_config.yaml'), 'wb') as f:
            anno_callback(f, task_data)

        make_zip_archive(temp_dir, dst_file)

@exporter(name='VL Site Config', ext='ZIP', version='0.1')
def _export_images(dst_file, task_data, save_images=False):
    _export(dst_file, task_data,
        anno_callback=dump_as_site_config, save_images=save_images)

@importer(name='VL Site Config', ext='YAML, ZIP', version='1.1')
def _import(src_file, task_data):
    is_zip = zipfile.is_zipfile(src_file)
    src_file.seek(0)
    if is_zip:
        with TemporaryDirectory() as tmp_dir:
            zipfile.ZipFile(src_file).extractall(tmp_dir)

            anno_paths = glob(osp.join(tmp_dir, '**', '*.yaml'), recursive=True)
            for p in anno_paths:
                load(p, task_data)
    else:
        load(src_file, task_data)
