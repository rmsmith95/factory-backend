import xml.etree.ElementTree as ET

def parse_xml_file(filename: str):
    """Parse an XML file into a dict-like structure."""
    tree = ET.parse(filename)
    root = tree.getroot()

    def elem_to_dict(elem):
        node = {elem.tag: {} if elem.attrib else None}
        children = list(elem)
        if children:
            dd = {}
            for child in children:
                child_dict = elem_to_dict(child)
                for k, v in child_dict.items():
                    if k in dd:
                        # if multiple children with same tag, convert to list
                        if not isinstance(dd[k], list):
                            dd[k] = [dd[k]]
                        dd[k].append(v)
                    else:
                        dd[k] = v
            node = {elem.tag: dd}
        if elem.attrib:
            node[elem.tag].update(('@' + k, v) for k, v in elem.attrib.items())
        if elem.text and elem.text.strip():
            text = elem.text.strip()
            if children or elem.attrib:
                node[elem.tag]['#text'] = text
            else:
                node[elem.tag] = text
        return node

    return elem_to_dict(root)
