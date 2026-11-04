/*
 * Carla JSON project document test
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Round-trips the project tree through JSON and back, including attributes,
 * repeated tags, empty elements, UTF-8 and \u escapes. Run with
 * scripts/test_json_document.sh
 */

#include <cstdio>

#include "CarlaJsonDocument.hpp"

static const char* const kProjectXml =
"<?xml version='1.0' encoding='UTF-8'?>\n"
"<!DOCTYPE CARLA-PROJECT>\n"
"<CARLA-PROJECT VERSION='2.0' IgnoreClientPrefix='true'>\n"
" <EngineSettings>\n"
"  <ForceStereo>false</ForceStereo>\n"
"  <PreferPluginBridges>false</PreferPluginBridges>\n"
" </EngineSettings>\n"
" <Plugin>\n"
"  <Info><Name>Dr\u00fcben &amp; Test</Name><URI>urn:test</URI></Info>\n"
"  <Parameters><Parameter id='0'>1.5</Parameter><Parameter id='1'>0</Parameter></Parameters>\n"
"  <Empty/>\n"
" </Plugin>\n"
"</CARLA-PROJECT>\n";

// what Python's json.dump produces for non-ASCII, plus frontend metadata that must be skipped
static const char* const kPythonJson =
"{\"format\": \"carla-project-json\", \"version\": \"1.0\","
" \"canvas_positions\": [{\"name\": \"A\"}],"
" \"CARLA-PROJECT\": {\"@attributes\": {\"VERSION\": \"2.0\"},"
" \"Plugin\": [{\"Info\": {\"Name\": \"Dr\\u00fcben\"}}, {\"Info\": {\"Name\": \"Second\"}}]}}";

int main()
{
    int failures = 0;

    const water::String json(CarlaJsonDocument::xmlToJson(water::String(kProjectXml)));

    if (json.isEmpty())
    {
        std::printf("FAIL: xmlToJson returned nothing\n");
        return 1;
    }

    const water::String backToXml(CarlaJsonDocument::jsonToXml(json));

    if (backToXml.isEmpty())
    {
        std::printf("FAIL: jsonToXml returned nothing\n");
        return 1;
    }

    water::XmlDocument doc(backToXml);
    const water::XmlElement* const root = doc.getDocumentElement();

    if (root == nullptr || ! root->hasTagName("CARLA-PROJECT"))
    {
        std::printf("FAIL: root element\n");
        return 1;
    }

    if (root->getStringAttribute("VERSION") != "2.0"
        || root->getStringAttribute("IgnoreClientPrefix") != "true")
    {
        std::printf("FAIL: root attributes\n");
        ++failures;
    }

    const water::XmlElement* const plugin = root->getChildByName("Plugin");
    const water::XmlElement* const info = plugin != nullptr ? plugin->getChildByName("Info") : nullptr;

    if (info == nullptr || info->getChildByName("Name")->getAllSubText() != "Dr\u00fcben & Test")
    {
        std::printf("FAIL: plugin name text\n");
        ++failures;
    }

    const water::XmlElement* const parameters = plugin != nullptr ? plugin->getChildByName("Parameters") : nullptr;

    if (parameters == nullptr || parameters->getNumChildElements() != 2
        || parameters->getChildElement(1)->getStringAttribute("id") != "1")
    {
        std::printf("FAIL: repeated tags\n");
        ++failures;
    }

    if (plugin == nullptr || plugin->getChildByName("Empty") == nullptr)
    {
        std::printf("FAIL: empty element\n");
        ++failures;
    }

    water::XmlDocument pyDoc(CarlaJsonDocument::jsonToXml(water::String(kPythonJson)));
    const water::XmlElement* const pyRoot = pyDoc.getDocumentElement();

    if (pyRoot == nullptr)
    {
        std::printf("FAIL: python json parse\n");
        return 1;
    }

    const water::XmlElement* const pyPlugins = pyRoot->getChildByName("Plugin");

    if (pyPlugins == nullptr || pyPlugins->getNextElement() == nullptr)
    {
        std::printf("FAIL: json array of plugins\n");
        ++failures;
    }
    else if (pyPlugins->getChildByName("Info")->getChildByName("Name")->getAllSubText() != "Dr\u00fcben")
    {
        std::printf("FAIL: \\u escape decode\n");
        ++failures;
    }
    else if (pyPlugins->getNextElement()->getChildByName("Info")->getChildByName("Name")->getAllSubText() != "Second")
    {
        std::printf("FAIL: second array entry\n");
        ++failures;
    }

    if (failures == 0)
        std::printf("json-document: all checks passed\n");

    return failures == 0 ? 0 : 1;
}
