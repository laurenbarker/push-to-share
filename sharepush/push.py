import logging
import uuid
import urlparse

import requests

from sharepush import settings


logger = logging.getLogger(__name__)


def push_normalizeddata(data):

    if not settings.ACCESS_TOKEN:
        raise ValueError('No access_token for {}. Unable to push {} to SHARE.'.format(settings.SOURCE_NAME, data))
    resp = requests.post('{}normalizeddata/'.format(settings.SHARE_URL), json={
        'data': {
            'type': 'NormalizedData',
            'attributes': {
                'tasks': [],
                'raw': None,
                'data': {'@graph': format_creativework(data)}
            }
        }
    }, headers={
        'Authorization': 'Bearer {}'.format(settings.ACCESS_TOKEN),
        'Content-Type': 'application/vnd.api+json'
    })
    logger.debug(resp.content)
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
    person = GraphNode('person', **{
        'suffix': agent.suffix,
        'given_name': agent.given_name,
        'family_name': agent.family_name,
        'additional_name': agent.middle_names,
    })

    person.attrs['identifiers'] = [GraphNode(
        'agentidentifier',
        agent=person,
        uri='mailto:{}'.format(uri)
    ) for uri in agent.emails]

    if agent.is_registered:
        person.attrs['identifiers'].append(GraphNode(
            'agentidentifier',
            agent=person,
            uri=agent.profile_image_url())
        )
        person.attrs['identifiers'].append(GraphNode(
            'agentidentifier',
            agent=person,
            uri=urlparse.urljoin(settings.DOMAIN, agent.profile_url))
        )

    person.attrs['related_agents'] = [GraphNode(
        'isaffiliatedwith',
        subject=person,
        related=GraphNode('institution', name=institution)
    ) for institution in agent.affiliated_institutions.values_list('name', flat=True)]

    return person


def format_contributor(creative_work, agent, bibliographic, index):
    return GraphNode(
        'creator' if bibliographic else 'contributor',
        agent=format_agent(agent),
        order_cited=index if bibliographic else None,
        creative_work=creative_work,
        cited_as=agent.fullname,
    )


def format_creativework(preprint):
    ''' Return graph of creativework

        Attributes (required):
            data.id (str): if updating or deleting use existing id (XXXXX-XXX-XXX),
                if creating use '_:X' for temporary id within graph
            data.type (str): SHARE creative work type

        Attributes (optional):
            data.title (str):
            data.description (str):
            data.identifiers (list):
            data.creators (list): bibliographic contributors
            data.contributors (list): non-bibliographic contributors
            data.date_published (date):
            data.date_updated (date):
            data.is_deleted (boolean): defaults to false
            data.tags (list): free text
            data.subjects (list): bepress taxonomy

        See 'https://staging-share.osf.io/api/v2/schema' for SHARE types
    '''
    preprint_graph = GraphNode('preprint', **{
        'title': preprint.node.title,
        'description': preprint.node.description or '',
        'is_deleted': (
            not preprint.is_published or
            not preprint.node.is_public or
            preprint.node.is_preprint_orphan or
            preprint.node.tags.filter(name='qatest').exists() or
            preprint.node.is_deleted
        ),
        'date_updated': preprint.date_modified.isoformat(),
        'date_published': preprint.date_published.isoformat() if preprint.date_published else None
    })

    to_visit = [
        preprint_graph,
        GraphNode(
            'workidentifier',
            creative_work=preprint_graph,
            uri=urlparse.urljoin(settings.DOMAIN, preprint.url)
        )
    ]

    if preprint.article_doi:
        to_visit.append(GraphNode(
            'workidentifier',
            creative_work=preprint_graph,
            uri='http://dx.doi.org/{}'.format(preprint.article_doi)
        ))

    preprint_graph.attrs['tags'] = [
        GraphNode(
            'throughtags',
            creative_work=preprint_graph,
            tag=GraphNode('tag', name=tag)
        ) for tag in preprint.node.tags.values_list('name', flat=True)
    ]

    preprint_graph.attrs['subjects'] = [
        GraphNode(
            'throughsubjects',
            creative_work=preprint_graph,
            subject=GraphNode('subject', name=subject)
        )
        for subject in set(x['text'] for hier in preprint.get_subjects() or [] for x in hier) if subject
    ]

    to_visit.extend(format_contributor(preprint_graph, user, preprint.node.get_visible(user), i) for i, user in enumerate(preprint.node.contributors))
    to_visit.extend(GraphNode('AgentWorkRelation', creative_work=preprint_graph, agent=GraphNode('institution', name=institution))
                    for institution in preprint.node.affiliated_institutions.values_list('name', flat=True))

    visited = set()
    to_visit.extend(preprint_graph.get_related())

    while True:
        if not to_visit:
            break
        n = to_visit.pop(0)
        if n in visited:
            continue
        visited.add(n)
        to_visit.extend(list(n.get_related()))

    return [node.serialize() for node in visited]
