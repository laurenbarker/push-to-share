import logging
import uuid
import requests

from sharepush import settings
from sharepush.data import get_data


logger = logging.getLogger(__name__)


def try_key(obj, key, default=''):
    try:
        return obj[key]
    except KeyError:
        return default


def load_data():
    data = get_data()
    for work in data['works']:
        push_normalizeddata(format_creativework(data['works'][work], data))


def push_normalizeddata(formatted_work):

    if not settings.ACCESS_TOKEN:
        raise ValueError('No access_token for {}. Unable to push {} to SHARE.'.format(settings.SOURCE_NAME, formatted_work))
    resp = requests.post('{}normalizeddata/'.format(settings.SHARE_URL), json={
        'data': {
            'type': 'NormalizedData',
            'attributes': {
                'tasks': [],
                'raw': None,
                'data': {'@graph': formatted_work}
            }
        }
    }, headers={
        'Authorization': 'Bearer {}'.format(settings.ACCESS_TOKEN),
        'Content-Type': 'application/vnd.api+json'
    })
    if resp.status_code == 400:
        print(formatted_work)
        print(resp.content)
    resp.raise_for_status()


class GraphNode(object):

    @property
    def ref(self):
        return {'@id': self.id, '@type': self.type}

    def __init__(self, type_, **attrs):
        self.id = '_:{}'.format(uuid.uuid4())
        self.type = type_.lower()
        self.attrs = attrs

    def get_related(self):
        for value in self.attrs.values():
            if isinstance(value, GraphNode):
                yield value
            elif isinstance(value, list):
                for val in value:
                    yield val

    def serialize(self):
        ser = {}
        for key, value in self.attrs.items():
            if isinstance(value, GraphNode):
                ser[key] = value.ref
            elif isinstance(value, list) or value in {None, ''}:
                continue
            else:
                ser[key] = value

        return dict(self.ref, **ser)


def format_agent(agent):
    person = GraphNode(agent['type'], **{
        'name': agent['name']
    })

    if try_key(agent, 'identifier', default=[]):
        person.attrs['identifiers'] = [
            GraphNode(
                'agentidentifier',
                agent=person,
                uri=agent['identifier']
            )
        ]

    person.attrs['related_agents'] = []

    if try_key(agent, 'affiliation', default=[]):
        person.attrs['related_agents'].extend([
            GraphNode(
                'isaffiliatedwith',
                subject=person,
                related=GraphNode('institution', name=affiliation.strip())
            ) for affiliation in agent['affiliation'].split("|")
        ])

    if try_key(agent, 'department', default=[]):
        person.attrs['related_agents'].extend([
            GraphNode(
                'isaffiliatedwith',
                subject=person,
                related=GraphNode('department', name=department.strip())
            ) for department in agent['department'].split("|")
        ])

    return person


def format_contributor(creative_work, agent, bibliographic, index):
    return GraphNode(
        'creator' if bibliographic else 'contributor',
        agent=format_agent(agent),
        order_cited=index if bibliographic else None,
        creative_work=creative_work,
        cited_as=agent['name'],
    )


def format_award(award):
    """
        name
        description
        award_amount
        date
        uri
    """
    return GraphNode(
        'award',
        name=award['title'],
        date=award['date'],
        uri=award['identifier'] if award['identifier'] else None
    )


def format_funder(creative_work, agent, awards_data):

    funder_graph = GraphNode(
        'funder',
        agent=format_agent(agent),
        creative_work=creative_work,
    )

    if agent['awards']:
        funder_graph.attrs['award'] = [
            GraphNode(
                'throughawards',
                funder=funder_graph,
                award=format_award(awards_data[award.strip()])
            ) for award in agent['awards'].split("|")
        ]

    return funder_graph


def format_creativework(work, data):
    ''' Return graph of creativework

        Attributes (required):
            id (str): if updating or deleting use existing id (XXXXX-XXX-XXX),
                if creating use '_:X' for temporary id within graph
            type (str): SHARE creative work type

        Attributes (optional):
            title (str):
            description (str):
            identifiers (list):
            creators (list): bibliographic contributors
            contributors (list): non-bibliographic contributors
            date_published (date):
            date_updated (date):
            is_deleted (boolean): defaults to false
            tags (list): free text
            subjects (list): bepress taxonomy

        See 'https://staging-share.osf.io/api/v2/schema' for SHARE types
    '''

    # work
    work_graph = GraphNode(work['type'], **{
        'title': work['title'],
        'description': work['description'],
        'is_deleted': False
        # 'date_updated': None,
        # 'date_published': None
    })

    # work identifier (i.e. DOI)
    graph = [
        work_graph,
        GraphNode(
            'workidentifier',
            creative_work=work_graph,
            uri=work['url']
        )
    ]

    # tags - free text
    work_graph.attrs['tags'] = [
        GraphNode(
            'throughtags',
            creative_work=work_graph,
            tag=GraphNode('tag', name=tag.strip())
        ) for tag in work['tags'].split('|')
    ]

    # creators/contributors
    if work['contributors']:
        graph.extend(
            format_contributor(
                work_graph,
                data['contributors'][user_id.strip()],
                True,
                i
            ) for i, user_id in enumerate(work['contributors'].split('|'))
        )

    # funders
    if work['funders']:
        graph.extend(
            format_funder(
                work_graph,
                data['funders'][funder_id.strip()],
                data['awards']
            ) for funder_id in work['funders'].split('|')
        )

    # related_works
    if work['related_works']:
        work_graph.attrs['related_works'] = [GraphNode(
            'WorkRelation',
            subject=work_graph,
            related=GraphNode('creativework', identifiers=[GraphNode(
                'workidentifier',
                creative_work=work_graph,
                uri=identifier.strip()
            )])
        ) for identifier in work['related_works'].split('|')]

    visited = set()
    graph.extend(work_graph.get_related())

    while True:
        if not graph:
            break
        n = graph.pop(0)
        if n in visited:
            continue
        visited.add(n)
        graph.extend(list(n.get_related()))

    return [node.serialize() for node in visited]
