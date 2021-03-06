from cfme.common.provider import BaseProvider
from cfme.fixtures import pytest_selenium as sel
from cfme.web_ui import (
    Region, Quadicon, Form, AngularSelect, form_buttons, Input, toolbar as tb, InfoBlock
)
from cfme.web_ui.menu import nav
from utils.browser import ensure_browser_open
from utils.db import cfmedb
from utils.pretty import Pretty

from . import cfg_btn, mon_btn, pol_btn

nav.add_branch(
    'containers_providers',
    {
        'containers_provider_new':
            lambda _: cfg_btn('Add a New Containers Provider'),
        'containers_provider':
        [
            lambda ctx: sel.check(Quadicon(ctx['provider'].name, None).checkbox),
            {
                'containers_provider_edit':
                lambda _: cfg_btn('Edit Selected Containers Provider'),
                'containers_provider_edit_tags':
                lambda _: pol_btn('Edit Tags')
            }],
        'containers_provider_detail':
        [
            lambda ctx: sel.click(Quadicon(ctx['provider'].name, None)),
            {
                'containers_provider_edit_detail':
                lambda _: cfg_btn('Edit this Containers Provider'),
                'containers_provider_timelines_detail':
                lambda _: mon_btn('Timelines'),
                'containers_provider_edit_tags_detail':
                lambda _: pol_btn('Edit Tags'),
                'containers_provider_topology_detail':
                lambda _: sel.click(InfoBlock('Overview', 'Topology'))
            }]
    }
)


properties_form = Form(
    fields=[
        ('type_select', AngularSelect('server_emstype')),
        ('name_text', Input('name')),
        ('hostname_text', Input('hostname')),
        ('port_text', Input('port')),
        # ('zone_select', AngularSelect('server_zone'))
    ])

details_page = Region(infoblock_type='detail')


class Provider(BaseProvider, Pretty):
    pretty_attrs = ['name', 'key', 'zone']
    STATS_TO_MATCH = [
        'num_project', 'num_service', 'num_replication_controller', 'num_pod', 'num_node',
        'num_container', 'num_image', 'num_image_registry']
    string_name = "Containers"
    page_name = "containers"
    detail_page_suffix = 'provider_detail'
    edit_page_suffix = 'provider_edit_detail'
    refresh_text = "Refresh items and relationships"
    quad_name = None
    properties_form = properties_form
    add_provider_button = form_buttons.FormButton("Add this Containers Provider")
    save_button = form_buttons.FormButton("Save Changes")

    def __init__(self, name=None, credentials=None, key=None,
                 zone=None, hostname=None, port=None, provider_data=None):
        if not credentials:
            credentials = {}
        self.name = name
        self.credentials = credentials
        self.key = key
        self.zone = zone
        self.hostname = hostname
        self.port = port
        self.provider_data = provider_data

    def _on_detail_page(self):
        """ Returns ``True`` if on the providers detail page, ``False`` if not."""
        ensure_browser_open()
        return sel.is_displayed('//div//h1[contains(., "{} (Summary)")]'.format(self.name))

    def load_details(self, refresh=False):
        if not self._on_detail_page():
            self.navigate(detail=True)
        elif refresh:
            tb.refresh()

    def navigate(self, detail=True):
        if detail is True:
            if not self._on_detail_page():
                sel.force_navigate('containers_provider_detail', context={'provider': self})
        else:
            sel.force_navigate('containers_provider', context={'provider': self})

    def get_detail(self, *ident):
        """ Gets details from the details infoblock

        Args:
            *ident: An InfoBlock title, followed by the Key name, e.g. "Relationships", "Images"
        Returns: A string representing the contents of the InfoBlock's value.
        """
        self.navigate(detail=True)
        return details_page.infoblock.text(*ident)

    def _num_db_generic(self, table_str):
        res = cfmedb().engine.execute(
            "SELECT count(*) "
            "FROM ext_management_systems, {0} "
            "WHERE {0}.ems_id=ext_management_systems.id "
            "AND ext_management_systems.name='{1}'".format(table_str, self.name))
        return int(res.first()[0])

    def num_project(self, db=True):
        if db:
            return self._num_db_generic('container_projects')
        else:
            return int(self.get_detail("Relationships", "Projects"))

    def num_service(self, db=True):
        if db:
            return self._num_db_generic('container_services')
        else:
            return int(self.get_detail("Relationships", "Services"))

    def num_replication_controller(self, db=True):
        if db:
            return self._num_db_generic('container_replicators')
        else:
            return int(self.get_detail("Relationships", "Replicators"))

    def num_container_group(self, db=True):
        if db:
            return self._num_db_generic('container_groups')
        else:
            return int(self.get_detail("Relationships", "Pods"))

    def num_pod(self, db=True):
        # potato tomato
        return self.num_container_group(db)

    def num_node(self, db=True):
        if db:
            return self._num_db_generic('container_nodes')
        else:
            return int(self.get_detail("Relationships", "Nodes"))

    def num_container(self, db=True):
        if db:
            # Containers are linked to providers through container definitions and then through pods
            res = cfmedb().engine.execute(
                "SELECT count(*) "
                "FROM ext_management_systems, container_groups, container_definitions, containers "
                "WHERE containers.container_definition_id=container_definitions.id "
                "AND container_definitions.container_group_id=container_groups.id "
                "AND container_groups.ems_id=ext_management_systems.id "
                "AND ext_management_systems.name='{}'".format(self.name))
            return int(res.first()[0])
        else:
            return int(self.get_detail("Relationships", "Containers"))

    def num_image(self, db=True):
        if db:
            return self._num_db_generic('container_images')
        else:
            return int(self.get_detail("Relationships", "Images"))

    def num_image_registry(self, db=True):
        if db:
            return self._num_db_generic('container_image_registries')
        else:
            return int(self.get_detail("Relationships", "Image Registries"))


class KubernetesProvider(Provider):

    def __init__(self, name=None, credentials=None, key=None,
                 zone=None, hostname=None, port=None, provider_data=None):
        super(KubernetesProvider, self).__init__(
            name=name, credentials=credentials, key=key, zone=zone, hostname=hostname, port=port,
            provider_data=provider_data)

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'Kubernetes',
                'hostname_text': kwargs.get('hostname'),
                'port_text': kwargs.get('port'),
                'zone_select': kwargs.get('zone')}


class OpenshiftProvider(Provider):
    STATS_TO_MATCH = Provider.STATS_TO_MATCH + ['num_route']

    def __init__(self, name=None, credentials=None, key=None,
                 zone=None, hostname=None, port=None, provider_data=None):
        super(OpenshiftProvider, self).__init__(
            name=name, credentials=credentials, key=key, zone=zone, hostname=hostname, port=port,
            provider_data=provider_data)

    def create(self, validate_credentials=True, **kwargs):
        # Workaround - randomly fails on 5.5.0.8 with no validation
        # probably a js wait issue, not reproducible manually
        super(OpenshiftProvider, self).create(validate_credentials=validate_credentials, **kwargs)

    def _form_mapping(self, create=None, **kwargs):
        return {'name_text': kwargs.get('name'),
                'type_select': create and 'OpenShift',
                'hostname_text': kwargs.get('hostname'),
                'port_text': kwargs.get('port'),
                'zone_select': kwargs.get('zone')}

    def num_route(self, db=True):
        if db:
            return self._num_db_generic('container_routes')
        else:
            return int(self.get_detail("Relationships", "Routes"))
