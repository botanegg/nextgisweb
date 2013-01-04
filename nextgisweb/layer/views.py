# -*- coding: utf-8 -*-
from pyramid.view import view_config
from pyramid.httpexceptions import HTTPFound
from pyramid.renderers import render_to_response

from ..wtforms import Form, fields, validators

from ..models import DBSession
from ..views import model_context, permalinker
from .. import action_panel as ap

from .models import Layer


def __action_panel(self, request):
    from ..style import Style

    new_style_items = []
    for style in Style.registry:
        if style.is_layer_supported(self):
            new_style_items.append(ap.I(
                style.cls_display_name,
                request.route_url('style.new', layer_id=self.id, _query=dict(identity=style.identity))
            ))

    panel = ap.P((
        ap.S('style-new', u"Добавить стиль", new_style_items),
        ap.S('manage', u"Управление", (
            ap.I(u"Управление доступом", request.route_url('layer.security', id=self.id)),
        )),
        ap.S('operation', u"Операции", (
            ap.I(u"Переместить", '#'),
            ap.I(u"Удалить", request.route_url('layer_group.delete', id=self.id)),
        )),
    ))

    return panel


Layer.__action_panel = __action_panel


from ..object_widget import ObjectWidget, CompositeWidget

class LayerObjectWidget(ObjectWidget):

    def populate_obj(self):
        ObjectWidget.populate_obj(self)

        self.obj.display_name = self.data['display_name']
        self.obj.keyname = self.data['keyname']

    def widget_module(self):
        return 'layer/Widget'

Layer.object_widget = LayerObjectWidget


@view_config(route_name='layer')
def home(request):
    raise HTTPFound(location=request.route_url('layer_group'))


@view_config(route_name='layer.show')
@model_context(Layer)
def show(request, obj):
    actual_class = Layer.registry[obj.cls]
    obj = DBSession.query(Layer) \
        .with_polymorphic((actual_class, ))\
        .filter_by(id=obj.id).one()

    return render_to_response(
        actual_class.__show_template,
        dict(obj=obj),
        request
    )


@view_config(route_name='layer.new')
def new(request):
    layer_group_id=int(request.GET['layer_group_id'])
    identity=request.GET['identity']

    cls = Layer.registry[identity]

    widget = CompositeWidget((
        ('layer', Layer.object_widget),
        (identity, cls.object_widget),
    ))

    if request.method == 'POST':
        widget.bind(data=request.json_body, request=request)
        # TODO: widget.validate()

        obj = cls(layer_group_id=layer_group_id)
        DBSession.add(obj)

        widget.bind(obj=obj)
        widget.populate_obj()

        DBSession.flush()
        return render_to_response('json', dict(url=obj.permalink(request)))

    return render_to_response(
        'layer/new.mako',
        dict(widget=widget),
        request
    )


permalinker(Layer, 'layer.show')


@view_config(route_name='layer.security')
@model_context(Layer)
def security_proxy(request, obj):
    from ..security.views import acl_editor_view
    return acl_editor_view(request, obj, obj.acl)
