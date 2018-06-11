import re
import subprocess
from subprocess import Popen, PIPE

if False:
    from typing import List, Dict, Tuple, Union, Optional, NamedTuple  # noqa: F401

import apertium  # noqa: F401
from apertium.utils import to_alpha3_code, execute, parse_mode_file  # noqa: F401


class Translator:

    def __init__(self, l1, l2):  # type: (Translator, str, str) -> None
        self.translation_cmds = {}  # type: Dict[Tuple[str, str], List[List[str]]]
        self.l1 = l1
        self.l2 = l2

    def _get_commands(self, l1, l2):  # type: (Translator, str, str) -> List[List[str]]
        if (l1, l2) not in self.translation_cmds:
            mode_path = apertium.pairs['%s-%s' % (l1, l2)]
            self.translation_cmds[(l1, l2)] = parse_mode_file(mode_path)
        return self.translation_cmds[(l1, l2)]

    def _get_pair_or_error(self):  # type: (Translator) -> Union[None, Tuple[str, str]]
        try:
            l1, l2 = map(to_alpha3_code, [self.l1, self.l2])
        except ValueError:
            return None
        if '%s-%s' % (l1, l2) not in apertium.pairs:
            return None
        else:
            return (l1, l2)

    def _get_format(self, format, deformat, reformat):
        # type: (Translator, Union[str, None], Union[str, None], Union[str, None]) -> Tuple[Union[str, None], Union[str, None]]
        if format:
            deformat = 'apertium-des' + format
            reformat = 'apertium-re' + format
        else:
            if 'apertium-des' not in deformat:  # type: ignore
                deformat = 'apertium-des' + deformat  # type: ignore
            if 'apertium-re' not in reformat:  # type: ignore
                reformat = 'apertium-re' + reformat  # type: ignore

        return deformat, reformat

    def _check_ret_code(self, name, proc):  # type: (Translator, str, Popen) -> None
        if proc.returncode != 0:
            raise subprocess.CalledProcessError()  # type: ignore

    def _validate_formatters(self, deformat, reformat):
        # type: (Translator, Union[str, None], Union[str, None]) -> Tuple[Union[str, object], Union[str, object]]
        def valid1(elt, lst):  # type: (Union[str, None], List[object]) -> Union[str, object]
            if elt in lst:
                return elt
            else:
                return lst[0]
        # First is fallback:
        deformatters = [
            'apertium-deshtml',
            'apertium-destxt',
            'apertium-desrtf',
            False,
        ]
        reformatters = [
            'apertium-rehtml-noent',
            'apertium-rehtml',
            'apertium-retxt',
            'apertium-rertf',
            False,
        ]
        return valid1(deformat, deformatters), valid1(reformat, reformatters)

    def _get_deformat(self, deformat, text):  # type: (Translator, str, str) -> str
        if deformat:
            proc_deformat = Popen(deformat, stdin=PIPE, stdout=PIPE)
            proc_deformat.stdin.write(bytes(text, 'utf-8'))
            deformatted = proc_deformat.communicate()[0]
            deformatted = deformatted.decode()
            self._check_ret_code('Deformatter', proc_deformat)
        else:
            deformatted = bytes(text, 'utf-8')
        res = str(deformatted)
        return res

    def _get_reformat(self, reformat, text):  # type: (Translator, str, str) -> str
        if reformat:
            proc_reformat = Popen(reformat, stdin=PIPE, stdout=PIPE)
            proc_reformat.stdin.write(bytes(text, 'utf-8'))
            result = proc_reformat.communicate()[0]
            self._check_ret_code('Reformatter', proc_reformat)
        else:
            result = re.sub(rb'\0$', b'', text)  # type: ignore
        return result  # type: ignore

    def translate(self, text, mark_unknown=False, format=None, deformat='txt', reformat='txt'):
        # type: (Translator, str, bool, Union[str, None], str, str) -> str
        pair = self._get_pair_or_error()
        if pair is not None:
            l1, l2 = pair
            cmds = list(self._get_commands(l1, l2))
            unsafe_deformat, unsafe_reformat = self._get_format(format, deformat, reformat)
            deformater, reformater = self._validate_formatters(unsafe_deformat, unsafe_reformat)
            deformatted = self._get_deformat(str(deformater), text)
            output = execute(deformatted, cmds)
            result = self._get_reformat(str(reformater), output).strip()
            return result.decode()  # type: ignore
        else:
            raise apertium.ModeNotInstalled()
