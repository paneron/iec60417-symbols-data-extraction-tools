#!/usr/bin/python

import datetime
import argparse

import re
import os
import glob

import yaml
import base64
import mimetypes

from pathlib import Path

import xml.etree.ElementTree as etree

from uuid import uuid5, NAMESPACE_OID as ns_oid


from iso639 import iso639
import config


def str_to_dt(date_str):
    return datetime.datetime.strptime(
        date_str, "%Y-%m-%d"
    ).date()


def read_xml(fname):
    with open(fname, "r") as _f:
        result = {
            "file": etree.parse(_f).getroot()
        }
        result["uuid"] = str(uuid5(ns_oid, etree.tostring(result["file"], encoding='unicode')))
        result["name"] = os.path.basename(os.path.splitext(fname)[0])
        return result


def read_xml_dir(dirname=None):
    result = []
    if dirname:
        alias = '/%s' % dirname
    else:
        dirname = ''

    xml_dir = "%s%s" % (config.input_dir, dirname)
    files = glob.glob("%s/*.xml" % xml_dir)
    for fname in files:
        data = read_xml(fname)
        result.append(data)

    return result


def save_yaml(uuid, data):
    file_path = config.output_dir
    Path(file_path).mkdir(parents=True, exist_ok=True)
    file = open("%s/%s.yaml" % (file_path, uuid), "w")
    file.write(yaml.dump(data, allow_unicode=True))
    file.close()


def l2_et_val(et):
    if len(et) > 0:
        result = []
        for txt in et.findall("text"):
            if txt.text:
                #text = re.sub(r"[\s\n]+", " ", txt.text)
                #text = ' '.join(txt.text.split())
                text = re.sub(r"[\n\t\s]+", " ", txt.text)
                result.append(text.strip())
        return result
    else:
        if et.text:
            return re.sub(r"[\n\t\s]+", " ", et.text.strip())


def uncap(s):
    return s[0].lower() + s[1:]


def to_list(elm):
    if elm and type(elm) == str:
        return [elm]
    elif type(elm) == list:
        return elm
    elif not elm:
        return []


def encode_file_base64(file_path):
    if Path(file_path).is_file():
        with open(file_path, 'rb') as binary_file:
            binary_file_data = binary_file.read()
            base64_encoded_data = base64.b64encode(binary_file_data)
            base64_message = base64_encoded_data.decode('utf-8')
            ext = Path(file_path).suffix
            mime_type = "application/octet-stream"
            if ext:
                mime_type = mimetypes.types_map[ext]
                return {
                    "mime": mime_type,
                    "data": base64_message,
                    "type": "base64"
                }


def convert_codes():
    source = read_xml_dir()

    items = []
    for elm in source:

        for symbol in elm["file"].findall("."):
            symbol_data = symbol.attrib
            symbol_data["form"] = {}

            for l1 in symbol:
                lang = lang_re.match(l1.tag)

                if lang:
                    tag_name = uncap(lang.group(1))

                    if not symbol_data.get(tag_name):
                        symbol_data[tag_name] = {}

                    alpha3 = iso639.get(lang.group(2).lower(), lang.group(2))

                    _val = l2_et_val(l1)
                    if _val:
                        symbol_data[tag_name][alpha3] = _val
                    else:
                        symbol_data[tag_name][alpha3] = ""

                else:
                    tag_name = uncap(l1.tag)
                    symbol_data[tag_name] = l2_et_val(l1)

                form = form_re.match(tag_name)
                if form:
                    symbol_data["form"][uncap(form.group(1))] = symbol_data.pop(tag_name)

        date_released = str_to_dt(symbol_data.pop("date_Released"))
        symbol_data["identifier"] = symbol_data.pop("iD")
        #symbol_data["cr"] = 
        symbol_data.pop("cR")
        symbol_data.pop("category")
        symbol_data.pop("modified")

        symbol_data["relevantPublications"] = to_list(symbol_data["relevantPublications"])
        symbol_data["fieldOfApplication"] = to_list(symbol_data["fieldOfApplication"])
        symbol_data["function"] = to_list(symbol_data["function"])
        symbol_data["geometricForm"] = to_list(symbol_data["geometricForm"])
        symbol_data["relevantTCs"] = to_list(symbol_data["relevantTCs"])
        symbol_data["replacing"] = to_list(symbol_data["replacing"])
        symbol_data["authors"] = to_list(symbol_data["authors"])

        for lng in symbol_data["description"]:
            if type(symbol_data["description"][lng]) == list:
                symbol_data["description"][lng] = ' '.join(symbol_data["description"][lng]).strip()
                if symbol_data["description"][lng][0:1] == '[' and  symbol_data["description"][lng][-1] == ']':
                    symbol_data["description"][lng] = symbol_data["description"][lng][1:-1]

        for lng in symbol_data["remarks"]:
            if type(symbol_data["remarks"][lng]) == list:
                symbol_data["remarks"][lng] = ' '.join(symbol_data["remarks"][lng]).strip()

        for lng in symbol_data["keywords"]:
            symbol_data["keywords"][lng] = to_list(symbol_data["keywords"][lng])

        attaches = symbol_data.pop("attachments")

        symbol_data["attachments"] = {}
        for fname in attaches:
            encoded_file = encode_file_base64('%s/%s' % (config.input_dir, fname))
            if encoded_file:
                if not symbol_data["attachments"].get(fname, False):
                    symbol_data["attachments"][fname] = encode_file_base64('%s/%s' % (config.input_dir, fname))
                else:
                    print("Duplicate filename: %s at %s (%s)" % (fname, elm["uuid"], symbol_data["identifier"]))
            else:
                symbol_data["attachments"][fname] = None

        preview_name = "%s.gif" % symbol_data["identifier"]
        preview_path = "%s/../preview/%s" % (config.input_dir, preview_name)

        if Path(preview_path).is_file():
            symbol_data["attachments"][preview_name] = encode_file_base64(preview_path)

        symbol = {
            "id": elm["uuid"],
            "dateAccepted": date_released,
            "status": "valid",
            "data": symbol_data
        }

        save_yaml(elm["uuid"], symbol)


lang_re = re.compile("^([A-z]+)_([A-Z]{2})$")
var_name = re.compile("^[A-Z]+$")
form_re = re.compile("^form([A-Z][A-z]+)$")


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Convert data from ICS code data to new yaml format."
    )
    convert_codes()
