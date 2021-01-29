# Copyright (C) 2018 Intel Corporation
#
# SPDX-License-Identifier: MIT

import os
import os.path as osp
import zipfile
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

            line = "\t" + shape.label + ": [["+ pts +"]]\n"
            file_object.write(str.encode(line))


def _export(dst_file, task_data, anno_callback, save_images=False):
    with TemporaryDirectory() as temp_dir:
        with open(osp.join(temp_dir, 'site_config.yaml'), 'wb') as f:
            anno_callback(f, task_data)

        make_zip_archive(temp_dir, dst_file)

@exporter(name='VL Site Config', ext='ZIP', version='0.1')
def _export_images(dst_file, task_data, save_images=False):
    _export(dst_file, task_data,
        anno_callback=dump_as_site_config, save_images=save_images)