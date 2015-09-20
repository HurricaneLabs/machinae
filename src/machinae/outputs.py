import io
import json


class MachinaeOutput:
    @staticmethod
    def get_formatter(format):
        if format.upper() == "N":
            return NormalOutput()
        elif format.upper() == "J":
            return JsonOutput()
        elif format.upper() == "D":
            return DotEscapedOutput()

    @staticmethod
    def escape(text):
        return str(text)

    def init_buffer(self):
        self._buffer = io.StringIO()

    def print(self, line, lf=True):
        self._buffer.write(line)
        if lf:
            self._buffer.write("\n")


class NormalOutput(MachinaeOutput):
    def output_header(self, target, otype, otype_detected):
        self.print("*" * 80)
        self.print("* Information for {0}".format(self.escape(target)))
        self.print("* Observable type: {0} (Auto-detected: {1})".format(otype, otype_detected))
        self.print("*" * 80)

    def run(self, result_sets):
        self.init_buffer()

        for row in result_sets:
            (target, otype, otype_detected) = row.target_info

            self.output_header(target, otype, otype_detected)
            self.print("")

            for item in row.results:
                site = item.site_info
                if hasattr(item, "error_info"):
                    self.print("[!] Error from {0}: {1}".format(site["name"], item.error_info))
                    continue

                if len(item.resultset) == 0:
                    self.print("[-] No {0} results".format(site["name"]))
                else:
                    self.print("[+] {0} results".format(site["name"]))
                    for result in item.resultset:
                        if len(result[0].values()) > 1:
                            values = map(repr, result[0].values())
                            values = map(self.escape, values)
                            output = "({0})".format(", ".join(values))
                        else:
                            output = self.escape(list(result[0].values())[0])
                        self.print("    [-] {1}: {0}".format(output, result[1]))

        return self._buffer.getvalue()


class DotEscapedOutput(NormalOutput):
    escapes = {
        ".": "\u2024",
        #".": "<dot>",
        #".": " DOT ",
        "@": " AT ",
        "http://": "",
        "https://": "",
    }

    def output_header(self, target, otype, otype_detected):
        super().output_header(target, otype, otype_detected)
        self.print("* These characters are escaped in the output below:")
        for (find, replace) in self.escapes.items():
            self.print("* '{0}' replaced with '{1}'".format(find, replace))
        self.print("* Do not click any links you find below")
        self.print("*" * 80)

    @classmethod
    def escape(cls, text):
        text = super(DotEscapedOutput, cls).escape(text)
        for (find, replace) in cls.escapes.items():
            text = text.replace(find, replace)
        return text


class JsonGenerator(MachinaeOutput):
    def run(self, result_sets):
        records = list()
        for row in result_sets:
            (target, otype, otype_detected) = row.target_info

            for item in row.results:
                output = dict()
                output["site"] = item.site_info["name"]
                output["results"] = dict()
                for result in item.resultset:
                    if result.pretty_name not in output["results"]:
                        output["results"][result.pretty_name] = list()
                    values = list(result.value.values())
                    if len(values) == 1:
                        output["results"][result.pretty_name].append(values[0])
                    elif len(values) > 1:
                        output["results"][result.pretty_name].append(values)
                for (k, v) in output["results"].items():
                    if len(v) == 1:
                        output["results"][k] = v[0]
                records.append(output)
        return records


class JsonOutput(JsonGenerator):
    def run(self, result_sets):
        self.init_buffer()

        for record in super().run(result_sets):
            self.print(json.dumps(record))

        return self._buffer.getvalue()
