# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

import os
import os.path as osp
import zipfile
import json
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

def dump_as_tl_config_json(file_object, annotations):

    for frame_annotation in annotations.group_by_frame(include_empty=True):
        config_obj = { "site_id": "8888", "groups_": {} }
        frame_id = frame_annotation.frame
        frame_width = float(frame_annotation.width)
        frame_height = float(frame_annotation.height)
        for shape in frame_annotation.labeled_shapes:
            if "tl" in shape.label:
                group_id = shape.label[6:-3]
                if group_id not in config_obj['groups_']:
                    config_obj['groups_'][group_id] = {'lights': []}

                x_points = []
                y_points = []
                for x, y in pairwise(shape.points):
                    x, y = (float(x) / frame_width), (float(y) / frame_height)
                    x_points.append(x)
                    y_points.append(y)
                x1, y1, x2, y2 = min(x_points), min(y_points), max(x_points), max(y_points)
                light = {
                    "light_id": str(len(config_obj['groups_'][group_id]['lights'])),
                    "orientation": "vertical" if x2-x1 < y2-y1 else "horizontal",
                    "region": [[str(x1),str(y1)],[str(x1),str(y2)],[str(x2),str(y1)],[str(x2),str(y2)]]
                }
                config_obj['groups_'][group_id]['lights'].append(light)

        config_obj['groups'] = []
        for k, v in config_obj['groups_'].items():
            group = {
                "group_id": k,
                "lights": v["lights"]
            }
            config_obj['groups'].append(group)
        del config_obj['groups_']
        file_object.write(str.encode(json.dumps(config_obj,indent=4)))


def load(file_object, annotations):

    for frame_annotation in annotations.group_by_frame(include_empty=True):
        frame_width = float(frame_annotation.width)
        frame_height = float(frame_annotation.height)

    data = json.load(file_object)
    for group in data['groups']:
        for light in group['lights']:
            x_points = []
            y_points = []
            for point in light['region']:
                x, y = point
                x, y = float(x) * frame_width, float(y) * frame_height
                x_points.append(x)
                y_points.append(y)
            x1, y1, x2, y2 = int(min(x_points)), int(min(y_points)), int(max(x_points)), int(max(y_points))

            shape = {}
            shape['attributes'] = []
            shape['frame'] = 0
            shape['label'] = 'group_'+group['group_id']+'_tl'
            shape['group'] = int(group['group_id'])
            shape['source'] = 'manual'

            shape['type'] = 'rectangle'
            shape['occluded'] = 0
            shape['z_order'] = 0

            shape['points'] = [float(x1),float(y1),float(x2),float(y2)]
            # for p in [[x1,y1],[x2,y2]]:
            #     shape['points'].extend(map(float, p))
            annotations.add_shape(annotations.LabeledShape(**shape))

def _export(dst_file, task_data, anno_callback, save_images=False):
    with TemporaryDirectory() as temp_dir:
        with open(osp.join(temp_dir, 'mesa_config.json'), 'wb') as f:
            anno_callback(f, task_data)

        make_zip_archive(temp_dir, dst_file)

@exporter(name='TL Status JSON Config', ext='ZIP', version='0.1')
def _export_images(dst_file, task_data, save_images=False):
    _export(dst_file, task_data,
        anno_callback=dump_as_tl_config_json, save_images=save_images)

@importer(name='TL Status JSON Config', ext='JSON, ZIP', version='1.1')
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
