import { init } from 'snabbdom';
import { VNode } from 'snabbdom/vnode'
import klass from 'snabbdom/modules/class';
import attributes from 'snabbdom/modules/attributes';
import * as Mousetrap  from 'mousetrap';
import Ctrl from './ctrl';

const patch = init([klass, attributes]);

import view from './view';
import { ServerData } from './types';

export function start(data: ServerData) {

  const element = document.querySelector('main') as HTMLElement;

  let vnode: VNode;

  function redraw() {
    vnode = patch(vnode, view(ctrl));
  }

  const ctrl = new Ctrl(data, redraw);

  const blueprint = view(ctrl);
  element.innerHTML = '';
  vnode = patch(element, blueprint);

  redraw();

  const noRepeat = (f: () => void) => (e: KeyboardEvent) => { if (!e.repeat) f() };

  Mousetrap.bind('left', ctrl.back);
  Mousetrap.bind('right', ctrl.forward);
  Mousetrap.bind('backspace', noRepeat(() => ctrl.review(false)));
  Mousetrap.bind('enter', noRepeat(() => ctrl.review(true)));
  Mousetrap.bind('a', () => (document.querySelector('a.analyse') as HTMLAnchorElement).click());
};
