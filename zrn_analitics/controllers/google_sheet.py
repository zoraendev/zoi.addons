# -*- coding: utf-8 -*-
import json
import posixpath
import re
from io import BytesIO
from zipfile import ZipFile
import xml.etree.ElementTree as ET

import requests

from odoo import http
from odoo.http import request


XML_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {"r": "http://schemas.openxmlformats.org/package/2006/relationships"}


class ZrnAnalyticsGoogleSheetController(http.Controller):
    @staticmethod
    def _get_json_payload():
        payload = {}
        raw_body = request.httprequest.data
        if raw_body:
            try:
                payload = json.loads(raw_body.decode("utf-8"))
            except (ValueError, UnicodeDecodeError):
                payload = {}
        return payload if isinstance(payload, dict) else {}

    @http.route(
        "/zrn_analitics/google_sheet/metadata",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def google_sheet_metadata(self, **kwargs):
        payload = self._get_json_payload()
        url = str(payload.get("url") or "").strip()
        try:
            workbook = self._fetch_google_sheet_metadata(url)
        except Exception as error:
            return request.make_json_response(
                {"success": False, "error": str(error) or "No se pudo leer el Google Sheet."},
                status=400,
            )
        return request.make_json_response({"success": True, "sheets": workbook})

    @http.route(
        "/zrn_analitics/google_sheet/sheet",
        type="http",
        auth="user",
        methods=["POST"],
        csrf=False,
    )
    def google_sheet_sheet(self, **kwargs):
        payload = self._get_json_payload()
        url = str(payload.get("url") or "").strip()
        sheet_index = int(payload.get("sheet_index") or 0)
        try:
            sheet = self._fetch_google_sheet_sheet(url, sheet_index)
        except Exception as error:
            return request.make_json_response(
                {"success": False, "error": str(error) or "No se pudo leer la hoja."},
                status=400,
            )
        return request.make_json_response({"success": True, "sheet": sheet})

    def _fetch_google_sheet_metadata(self, url):
        spreadsheet_id = self._extract_spreadsheet_id(url)
        archive = self._download_google_sheet_archive(spreadsheet_id)
        workbook_root, workbook_rels = self._read_workbook_roots(archive)
        rel_map = {
            rel.attrib.get("Id"): rel.attrib.get("Target")
            for rel in workbook_rels.findall("r:Relationship", REL_NS)
        }
        sheets = []
        for index, sheet_node in enumerate(workbook_root.findall("a:sheets/a:sheet", XML_NS)):
            rel_id = sheet_node.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            target = rel_map.get(rel_id)
            if not target:
                continue
            sheets.append({
                "index": index,
                "name": sheet_node.attrib.get("name") or f"Hoja {index + 1}",
            })
        return sheets

    def _fetch_google_sheet_sheet(self, url, sheet_index):
        spreadsheet_id = self._extract_spreadsheet_id(url)
        archive = self._download_google_sheet_archive(spreadsheet_id)
        workbook_root, workbook_rels = self._read_workbook_roots(archive)
        rel_map = {
            rel.attrib.get("Id"): rel.attrib.get("Target")
            for rel in workbook_rels.findall("r:Relationship", REL_NS)
        }
        shared_strings = self._read_shared_strings(archive)
        sheets = workbook_root.findall("a:sheets/a:sheet", XML_NS)
        if sheet_index < 0 or sheet_index >= len(sheets):
            raise ValueError("La hoja solicitada no existe en el workbook.")
        workbook_dir = "xl"
        sheet_node = sheets[sheet_index]
        rel_id = sheet_node.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
        target = rel_map.get(rel_id)
        if not target:
            raise ValueError("No se pudo resolver la hoja solicitada.")
        sheet_path = posixpath.normpath(posixpath.join(workbook_dir, target))
        raw_rows = self._read_sheet_rows(archive, sheet_path, shared_strings)
        return {
            "index": sheet_index,
            "name": sheet_node.attrib.get("name") or f"Hoja {sheet_index + 1}",
            "rawRows": raw_rows,
        }

    def _download_google_sheet_archive(self, spreadsheet_id):
        export_url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}/export?format=xlsx"
        response = requests.get(export_url, timeout=(10, 90))
        response.raise_for_status()
        return ZipFile(BytesIO(response.content))

    def _read_workbook_roots(self, archive):
        workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
        workbook_rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        return workbook_root, workbook_rels

    def _extract_spreadsheet_id(self, url):
        match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url or "")
        if not match:
            raise ValueError("La URL del Google Sheet no es valida.")
        return match.group(1)

    def _read_shared_strings(self, archive):
        if "xl/sharedStrings.xml" not in archive.namelist():
            return []
        root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
        values = []
        for item in root.findall("a:si", XML_NS):
            text = "".join(node.text or "" for node in item.findall(".//a:t", XML_NS))
            values.append(text)
        return values

    def _read_sheet_rows(self, archive, sheet_path, shared_strings):
        root = ET.fromstring(archive.read(sheet_path))
        rows = []
        previous_row = 0
        for row_node in root.findall("a:sheetData/a:row", XML_NS):
            row_number = int(row_node.attrib.get("r", previous_row + 1))
            while previous_row + 1 < row_number:
                rows.append([])
                previous_row += 1
            row_values = []
            previous_column = -1
            for cell_node in row_node.findall("a:c", XML_NS):
                cell_ref = cell_node.attrib.get("r", "")
                column_index = self._column_letters_to_index(re.sub(r"\d", "", cell_ref))
                while previous_column + 1 < column_index:
                    row_values.append("")
                    previous_column += 1
                row_values.append(self._read_cell_value(cell_node, shared_strings))
                previous_column = column_index
            rows.append(row_values)
            previous_row = row_number
        return rows

    def _read_cell_value(self, cell_node, shared_strings):
        cell_type = cell_node.attrib.get("t")
        if cell_type == "inlineStr":
            return "".join(node.text or "" for node in cell_node.findall(".//a:t", XML_NS))
        value_node = cell_node.find("a:v", XML_NS)
        if value_node is None or value_node.text is None:
            return ""
        raw_value = value_node.text
        if cell_type == "s":
            try:
                return shared_strings[int(raw_value)]
            except (ValueError, IndexError):
                return ""
        if cell_type == "b":
            return "true" if raw_value == "1" else "false"
        return raw_value

    def _column_letters_to_index(self, letters):
        index = 0
        for letter in letters:
            if not letter.isalpha():
                continue
            index = index * 26 + (ord(letter.upper()) - 64)
        return max(0, index - 1)
