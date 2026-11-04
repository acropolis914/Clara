/*
 * Carla JSON project document
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * Converts between the engine's water::XmlElement project tree and the JSON
 * project format used by .carjp files. Keeping this at the tree level means
 * the project serializer itself (CarlaEngine::saveProjectInternal and
 * loadProjectInternal) stays exactly as it is, and no XML ever reaches disk.
 */

#pragma once

#include <cstdio>
#include <memory>

#include "water/streams/MemoryOutputStream.h"
#include "water/text/Identifier.h"
#include "water/text/String.h"
#include "water/xml/XmlDocument.h"
#include "water/xml/XmlElement.h"

namespace CarlaJsonDocument {

// ------------------------------------------------------------------------------------------------------------
// XML element -> JSON text

static water::String elementText(const water::XmlElement& elem)
{
    water::MemoryOutputStream mem(64);

    for (const water::XmlElement* child = elem.getFirstChildElement(); child != nullptr; child = child->getNextElement())
    {
        if (child->isTextElement())
            mem << child->getText();
    }

    return mem.toUTF8().trim();
}

static void writeEscaped(water::MemoryOutputStream& out, const water::String& text)
{
    out << '"';

    for (const char* p = text.toRawUTF8(); *p != '\0'; ++p)
    {
        const unsigned char c = (unsigned char)*p;

        switch (c)
        {
        case '"':  out << "\\\""; break;
        case '\\': out << "\\\\"; break;
        case '\b': out << "\\b";  break;
        case '\f': out << "\\f";  break;
        case '\n': out << "\\n";  break;
        case '\r': out << "\\r";  break;
        case '\t': out << "\\t";  break;
        default:
            if (c < 0x20)
            {
                char buf[8];
                std::snprintf(buf, sizeof(buf), "\\u%04x", (unsigned int)c);
                out << buf;
            }
            else
            {
                out.writeByte((char)c); // UTF-8 bytes pass through untouched
            }
            break;
        }
    }

    out << '"';
}

static void writeIndent(water::MemoryOutputStream& out, const int depth)
{
    for (int i = 0; i < depth; ++i)
        out << '\t';
}

static int countElementChildren(const water::XmlElement& elem)
{
    int count = 0;

    for (const water::XmlElement* child = elem.getFirstChildElement(); child != nullptr; child = child->getNextElement())
    {
        if (! child->isTextElement())
            ++count;
    }

    return count;
}

static bool isPlainTextLeaf(const water::XmlElement& elem)
{
    return elem.getNumAttributes() == 0
        && countElementChildren(elem) == 0
        && elementText(elem).isNotEmpty();
}

static void writeValue(water::MemoryOutputStream& out, const water::XmlElement& elem, const int depth);

static void writeObject(water::MemoryOutputStream& out, const water::XmlElement& elem, const int depth)
{
    const int numAttributes = elem.getNumAttributes();
    const int numChildren   = elem.getNumChildElements();
    const int numElements   = countElementChildren(elem);
    const water::String text(elementText(elem));

    bool first = true;

    const auto beginMember = [&out, &first, depth]() {
        if (! first)
            out << ',';
        first = false;
        out << '\n';
        writeIndent(out, depth + 1);
    };

    out << '{';

    if (numAttributes > 0)
    {
        beginMember();
        out << "\"@attributes\": {";

        for (int i = 0; i < numAttributes; ++i)
        {
            if (i > 0)
                out << ", ";

            writeEscaped(out, water::String(elem.getAttributeName(i)));
            out << ": ";
            writeEscaped(out, elem.getAttributeValue(i));
        }

        out << '}';
    }

    if (numElements == 0)
    {
        if (text.isNotEmpty())
        {
            beginMember();
            out << "\"#text\": ";
            writeEscaped(out, text);
        }
    }
    else
    {
        // one key per distinct child tag, in first-appearance order; repeated tags become arrays
        for (int i = 0; i < numChildren; ++i)
        {
            const water::XmlElement* child = elem.getChildElement(i);

            if (child->isTextElement())
                continue;

            bool seenBefore = false;

            for (int j = 0; j < i && ! seenBefore; ++j)
            {
                const water::XmlElement* previous = elem.getChildElement(j);
                seenBefore = ! previous->isTextElement() && previous->getTagName() == child->getTagName();
            }

            if (seenBefore)
                continue;

            int count = 0;

            for (int j = 0; j < numChildren; ++j)
            {
                const water::XmlElement* other = elem.getChildElement(j);

                if (! other->isTextElement() && other->getTagName() == child->getTagName())
                    ++count;
            }

            beginMember();
            writeEscaped(out, child->getTagName());
            out << ": ";

            if (count > 1)
            {
                out << '[';

                bool firstItem = true;

                for (int j = 0; j < numChildren; ++j)
                {
                    const water::XmlElement* other = elem.getChildElement(j);

                    if (other->isTextElement() || other->getTagName() != child->getTagName())
                        continue;

                    if (! firstItem)
                        out << ',';

                    firstItem = false;
                    out << '\n';
                    writeIndent(out, depth + 2);
                    writeValue(out, *other, depth + 2);
                }

                out << '\n';
                writeIndent(out, depth + 1);
                out << ']';
            }
            else
            {
                writeValue(out, *child, depth + 1);
            }
        }

        if (text.isNotEmpty())
        {
            beginMember();
            out << "\"#text\": ";
            writeEscaped(out, text);
        }
    }

    if (! first)
    {
        out << '\n';
        writeIndent(out, depth);
    }

    out << '}';
}

static void writeValue(water::MemoryOutputStream& out, const water::XmlElement& elem, const int depth)
{
    if (isPlainTextLeaf(elem))
    {
        writeEscaped(out, elementText(elem));
        return;
    }

    writeObject(out, elem, depth);
}

water::String xmlToJson(const water::String& xmlText)
{
    water::XmlDocument doc(xmlText);
    const std::unique_ptr<water::XmlElement> root(doc.getDocumentElement());

    if (root == nullptr)
        return water::String();

    water::MemoryOutputStream out(4096);
    out << "{\n";
    out << "\t\"format\": \"carla-project-json\",\n";
    out << "\t\"version\": \"1.0\",\n";
    out << "\t\"CARLA-PROJECT\": ";
    writeValue(out, *root, 1);
    out << "\n}";

    return out.toUTF8();
}

// ------------------------------------------------------------------------------------------------------------
// JSON text -> XML element

static void appendUtf8(water::MemoryOutputStream& mem, const unsigned int codePoint)
{
    if (codePoint < 0x80)
    {
        mem.writeByte((char)codePoint);
    }
    else if (codePoint < 0x800)
    {
        mem.writeByte((char)(0xC0 | (codePoint >> 6)));
        mem.writeByte((char)(0x80 | (codePoint & 0x3F)));
    }
    else if (codePoint < 0x10000)
    {
        mem.writeByte((char)(0xE0 | (codePoint >> 12)));
        mem.writeByte((char)(0x80 | ((codePoint >> 6) & 0x3F)));
        mem.writeByte((char)(0x80 | (codePoint & 0x3F)));
    }
    else
    {
        mem.writeByte((char)(0xF0 | (codePoint >> 18)));
        mem.writeByte((char)(0x80 | ((codePoint >> 12) & 0x3F)));
        mem.writeByte((char)(0x80 | ((codePoint >> 6) & 0x3F)));
        mem.writeByte((char)(0x80 | (codePoint & 0x3F)));
    }
}

class JsonParser
{
public:
    explicit JsonParser(const char* const text)
        : p(text) {}

    water::XmlElement* parseDocument()
    {
        skipWhitespace();

        if (! expect('{'))
            return nullptr;

        std::unique_ptr<water::XmlElement> root;
        skipWhitespace();

        if (peek() == '}')
        {
            ++p;
            return nullptr;
        }

        while (true)
        {
            skipWhitespace();

            water::String key;

            if (! parseString(key))
                return nullptr;

            skipWhitespace();

            if (! expect(':'))
                return nullptr;

            skipWhitespace();

            if (key == "CARLA-PROJECT")
            {
                std::unique_ptr<water::XmlElement> elem(new water::XmlElement("CARLA-PROJECT"));

                if (! parseObjectInto(*elem))
                    return nullptr;

                root = std::move(elem);
            }
            else
            {
                // frontend metadata (format, version, patchbay containers, ...) is not engine data
                std::unique_ptr<water::XmlElement> scratch(new water::XmlElement("scratch"));

                if (peek() == '[')
                {
                    if (! parseArray("scratch", *scratch))
                        return nullptr;
                }
                else if (! parseValueInto("scratch", *scratch))
                {
                    return nullptr;
                }
            }

            skipWhitespace();

            const char c = peek();

            if (c == ',')
            {
                ++p;
                continue;
            }

            if (c == '}')
            {
                ++p;
                break;
            }

            return nullptr;
        }

        return root.release();
    }

private:
    const char* p;

    char peek() const noexcept { return *p; }

    void skipWhitespace() noexcept
    {
        while (*p == ' ' || *p == '\t' || *p == '\n' || *p == '\r')
            ++p;
    }

    bool expect(const char c) noexcept
    {
        if (*p != c)
            return false;

        ++p;
        return true;
    }

    bool parseHex4(unsigned int& value) noexcept
    {
        value = 0;

        for (int i = 0; i < 4; ++i)
        {
            const char c = *p;
            int digit;

            if (c >= '0' && c <= '9')
                digit = c - '0';
            else if (c >= 'a' && c <= 'f')
                digit = c - 'a' + 10;
            else if (c >= 'A' && c <= 'F')
                digit = c - 'A' + 10;
            else
                return false;

            value = (value << 4) | (unsigned int)digit;
            ++p;
        }

        return true;
    }

    bool parseString(water::String& result)
    {
        if (! expect('"'))
            return false;

        water::MemoryOutputStream mem(64);

        while (true)
        {
            const char c = *p;

            if (c == '\0')
                return false;

            if (c == '"')
            {
                ++p;
                break;
            }

            if (c == '\\')
            {
                ++p;
                const char escaped = *p;

                if (escaped == '\0')
                    return false;

                ++p;

                switch (escaped)
                {
                case '"':  mem.writeByte('"');  break;
                case '\\': mem.writeByte('\\'); break;
                case '/':  mem.writeByte('/');  break;
                case 'b':  mem.writeByte('\b'); break;
                case 'f':  mem.writeByte('\f'); break;
                case 'n':  mem.writeByte('\n'); break;
                case 'r':  mem.writeByte('\r'); break;
                case 't':  mem.writeByte('\t'); break;
                case 'u':
                {
                    unsigned int codePoint;

                    if (! parseHex4(codePoint))
                        return false;

                    if (codePoint >= 0xD800 && codePoint <= 0xDBFF && p[0] == '\\' && p[1] == 'u')
                    {
                        const char* const save = p;
                        unsigned int low;

                        p += 2;

                        if (parseHex4(low) && low >= 0xDC00 && low <= 0xDFFF)
                            codePoint = 0x10000 + ((codePoint - 0xD800) << 10) + (low - 0xDC00);
                        else
                            p = save;
                    }

                    appendUtf8(mem, codePoint);
                    break;
                }
                default:
                    return false;
                }

                continue;
            }

            mem.writeByte(c);
            ++p;
        }

        result = mem.toUTF8();
        return true;
    }

    bool parseScalarToken(water::String& token)
    {
        const char* const start = p;

        while (*p != '\0' && *p != ',' && *p != ']' && *p != '}'
               && *p != ' ' && *p != '\t' && *p != '\n' && *p != '\r')
        {
            ++p;
        }

        if (p == start)
            return false;

        token = water::String(start, (size_t)(p - start));
        return true;
    }

    bool parseAttributes(water::XmlElement& elem)
    {
        if (! expect('{'))
            return false;

        skipWhitespace();

        if (peek() == '}')
        {
            ++p;
            return true;
        }

        while (true)
        {
            skipWhitespace();

            water::String name;

            if (! parseString(name))
                return false;

            skipWhitespace();

            if (! expect(':'))
                return false;

            skipWhitespace();

            water::String value;

            if (! parseString(value))
                return false;

            elem.setAttribute(water::Identifier(name.toRawUTF8()), value);
            skipWhitespace();

            const char c = peek();

            if (c == ',')
            {
                ++p;
                continue;
            }

            if (c == '}')
            {
                ++p;
                return true;
            }

            return false;
        }
    }

    bool parseValueInto(const water::String& tag, water::XmlElement& parent)
    {
        skipWhitespace();

        const char c = peek();

        if (c == '{')
        {
            std::unique_ptr<water::XmlElement> child(new water::XmlElement(tag));

            if (! parseObjectInto(*child))
                return false;

            parent.addChildElement(child.release());
            return true;
        }

        if (c == '"')
        {
            water::String text;

            if (! parseString(text))
                return false;

            std::unique_ptr<water::XmlElement> child(new water::XmlElement(tag));
            child->addTextElement(text);
            parent.addChildElement(child.release());
            return true;
        }

        water::String token;

        if (! parseScalarToken(token))
            return false;

        std::unique_ptr<water::XmlElement> child(new water::XmlElement(tag));

        if (token.isNotEmpty() && token != "null")
            child->addTextElement(token);

        parent.addChildElement(child.release());
        return true;
    }

    bool parseArray(const water::String& tag, water::XmlElement& parent)
    {
        if (! expect('['))
            return false;

        skipWhitespace();

        if (peek() == ']')
        {
            ++p;
            return true;
        }

        while (true)
        {
            if (! parseValueInto(tag, parent))
                return false;

            skipWhitespace();

            const char c = peek();

            if (c == ',')
            {
                ++p;
                skipWhitespace();
                continue;
            }

            if (c == ']')
            {
                ++p;
                return true;
            }

            return false;
        }
    }

    bool parseObjectInto(water::XmlElement& elem)
    {
        if (! expect('{'))
            return false;

        skipWhitespace();

        if (peek() == '}')
        {
            ++p;
            return true;
        }

        while (true)
        {
            skipWhitespace();

            water::String key;

            if (! parseString(key))
                return false;

            skipWhitespace();

            if (! expect(':'))
                return false;

            skipWhitespace();

            if (key == "@attributes")
            {
                if (! parseAttributes(elem))
                    return false;
            }
            else if (key == "#text")
            {
                water::String text;

                if (! parseString(text))
                    return false;

                elem.addTextElement(text);
            }
            else if (peek() == '[')
            {
                if (! parseArray(key, elem))
                    return false;
            }
            else if (! parseValueInto(key, elem))
            {
                return false;
            }

            skipWhitespace();

            const char c = peek();

            if (c == ',')
            {
                ++p;
                continue;
            }

            if (c == '}')
            {
                ++p;
                return true;
            }

            return false;
        }
    }

    JsonParser(const JsonParser&);
    JsonParser& operator=(const JsonParser&);
};

water::String jsonToXml(const water::String& jsonText)
{
    JsonParser parser(jsonText.toRawUTF8());
    const std::unique_ptr<water::XmlElement> root(parser.parseDocument());

    if (root == nullptr)
        return water::String();

    water::MemoryOutputStream out(4096);
    root->writeToStream(out, water::StringRef(), false, true, "UTF-8", 0);

    return out.toUTF8();
}

} // namespace CarlaJsonDocument
