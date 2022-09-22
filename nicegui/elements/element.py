from __future__ import annotations

import asyncio
from typing import Dict, Optional

import justpy as jp

from ..binding import BindableProperty, bind_from, bind_to
from ..page import Page, get_current_view
from ..task_logger import create_task


def _handle_visibility_change(sender: Element, visible: bool) -> None:
    (sender.view.remove_class if visible else sender.view.set_class)('hidden')
    sender.update()


class Element:
    visible = BindableProperty(on_change=_handle_visibility_change)

    def __init__(self, view: jp.HTMLBaseComponent):
        self.parent_view = get_current_view()
        self.parent_view.add(view)
        self.view = view
        assert len(self.parent_view.pages) == 1
        self.page: Page = list(self.parent_view.pages.values())[0]
        self.view.add_page(self.page)

        self.visible = True

    def bind_visibility_to(self, target_object, target_name, forward=lambda x: x):
        bind_to(self, 'visible', target_object, target_name, forward=forward)
        return self

    def bind_visibility_from(self, target_object, target_name, backward=lambda x: x, *, value=None):
        if value is not None:
            def backward(x): return x == value

        bind_from(self, 'visible', target_object, target_name, backward=backward)
        return self

    def bind_visibility(self, target_object, target_name, forward=lambda x: x, backward=None, *, value=None):
        if value is not None:
            def backward(x): return x == value

        bind_from(self, 'visible', target_object, target_name, backward=backward)
        bind_to(self, 'visible', target_object, target_name, forward=forward)
        return self

    def classes(self, add: Optional[str] = None, *, remove: Optional[str] = None, replace: Optional[str] = None):
        '''HTML classes to modify the look of the element.
        Every class in the `remove` parameter will be removed from the element.
        Classes are separated with a blank space.
        This can be helpful if the predefined classes by NiceGUI are not wanted in a particular styling.
        '''
        class_list = self.view.classes.split() if replace is None else []
        class_list = [c for c in class_list if c not in (remove or '').split()]
        class_list += (add or '').split()
        class_list += (replace or '').split()
        new_classes = ' '.join(dict.fromkeys(class_list))  # NOTE: remove duplicates while preserving order
        if self.view.classes != new_classes:
            self.view.classes = new_classes
            self.update()
        return self

    def style(self, add: Optional[str] = None, *, remove: Optional[str] = None, replace: Optional[str] = None):
        '''CSS style sheet definitions to modify the look of the element.
        Every style in the `remove` parameter will be removed from the element.
        Styles are separated with a semicolon.
        This can be helpful if the predefined style sheet definitions by NiceGUI are not wanted in a particular styling.
        '''
        def str_to_dict(s: Optional[str]) -> Dict[str, str]:
            return dict((word.strip() for word in part.split(':')) for part in s.split(';')) if s else {}
        style_dict = str_to_dict((self.view.style or '').strip('; ')) if replace is None else {}
        for key in str_to_dict(remove):
            del style_dict[key]
        style_dict.update(str_to_dict(add))
        style_dict.update(str_to_dict(replace))
        new_style = ';'.join(f'{key}:{value}' for key, value in style_dict.items())
        if self.view.style != new_style:
            self.view.style = new_style
            self.update()
        return self

    def props(self, add: Optional[str] = None, *, remove: Optional[str] = None):
        '''Quasar props https://quasar.dev/vue-components/button#design to modify the look of the element.
        Boolean props will automatically activated if they appear in the list of the `add` property.
        Props are separated with a blank space.
        Every prop passed to the `remove` parameter will be removed from the element.
        This can be helpful if the predefined props by NiceGUI are not wanted in a particular styling.
        '''
        def str_to_dict(s: Optional[str]) -> Dict[str, str]:
            return {prop.split('=')[0]: prop.split('=')[1] if '=' in prop else True for prop in s.split()} if s else {}
        needs_update = False
        for key in str_to_dict(remove):
            if getattr(self.view, key, None) is not None:
                needs_update = True
            setattr(self.view, key, None)
        for key, value in str_to_dict(add).items():
            if getattr(self.view, key, None) != value:
                needs_update = True
            setattr(self.view, key, value)
        if needs_update:
            self.update()
        return self

    def tooltip(self, text: str, *, props: str = ''):
        tooltip = jp.QTooltip(text=text, temp=False)
        for prop in props.split():
            if '=' in prop:
                setattr(tooltip, *prop.split('='))
            else:
                setattr(tooltip, prop, True)
        tooltip.add_page(self.page)
        self.view.add(tooltip)
        self.update()
        return self

    def update(self) -> None:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return
        create_task(self.view.update())
