"""
Copyright BOOSTRY Co., Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.

You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.

See the License for the specific language governing permissions and
limitations under the License.

SPDX-License-Identifier: Apache-2.0
"""
from rich.panel import Panel
from rich.text import Text
from textual.widget import Widget

from gui import styles

UP = "\u2191"
DOWN = "\u2193"
LEFT = "\u2190"
RIGHT = "\u2192"
RIGHT_TRIANGLE = "\u25B6"
BIG_RIGHT_TRIANGLE = "\uE0B0"
DOWN_TRIANGLE = "\u25BC"

THINKING_FACE = ":thinking_face:"
FIRE = ":fire:"
INFO = "[blue]:information:[/]"


class Error(Widget):
    message = ""

    def render(self) -> Panel:
        text = Text.from_markup("{}".format(self.message))
        return Panel(
            text,
            title="{} [bold]error[/]".format(FIRE),
            border_style=styles.BORDER_ERROR,
            box=styles.BOX,
            title_align="left",
        )
