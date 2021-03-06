# -*- coding: utf-8 -*-
"""
This file contains all the HTTP routes for basic pages (usually HTML)
"""
from flask import Blueprint, Response, request, render_template
import pyldapi
import json
from rdflib import Graph
import io
import requests
import _config as config
import os
import controller.LOCIDatasetRenderer

pages = Blueprint('routes', __name__)


@pages.route('/', strict_slashes=True)
def home():
    return controller.LOCIDatasetRenderer.LOCIDatasetRenderer(request).render()


@pages.route('/index.ttl')
def home_ttl():
    return controller.LOCIDatasetRenderer.LOCIDatasetRenderer(request, view='dcat', format='text/turtle').render()


@pages.route('/about')
def about():
    return render_template(
        'page_about.html'
    )


@pages.route('/sparql.ttl', methods=['GET'])
def sparql_description():
    path_parts = request.path.rsplit('/', 1)
    path_parts = list(filter(bool, path_parts))
    if len(path_parts) == 1:
        path_parent = '/'
    else:
        path_parent = path_parts[0]
    base_url = request.host_url.rstrip('/') + path_parent
    return Response(
        get_sparql_service_description(
            format='turtle', base_url=base_url),
        status=200,
        mimetype='text/turtle')


@pages.route('/sparql', methods=['GET', 'POST'])
def sparql():
    # Query submitted
    if request.method == 'POST':
        '''Pass on the SPARQL query to the underlying system (Fuseki etc.)
        '''
        query = None
        if request.content_type == 'application/x-www-form-urlencoded':
            '''
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-post-urlencoded

            2.1.2 query via POST with URL-encoded parameters

            Protocol clients may send protocol requests via the HTTP POST method by URL encoding the parameters. When
            using this method, clients must URL percent encode all parameters and include them as parameters within the
            request body via the application/x-www-form-urlencoded media type with the name given above. Parameters must
            be separated with the ampersand (&) character. Clients may include the parameters in any order. The content
            type header of the HTTP request must be set to application/x-www-form-urlencoded.
            '''
            if request.form.get('query') is None or len(request.form.get('query')) < 5:
                return Response(
                    'Your POST request to the SPARQL endpoint must contain a \'query\' parameter if form posting '
                    'is used.',
                    status=400,
                    mimetype='text/plain'
                )
            else:
                query = request.form.get('query')
        elif request.content_type == 'application/sparql-query':
            '''
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-post-direct

            2.1.3 query via POST directly

            Protocol clients may send protocol requests via the HTTP POST method by including the query directly and
            unencoded as the HTTP request message body. When using this approach, clients must include the SPARQL query
            string, unencoded, and nothing else as the message body of the request. Clients must set the content type
            header of the HTTP request to application/sparql-query. Clients may include the optional default-graph-uri
            and named-graph-uri parameters as HTTP query string parameters in the request URI. Note that UTF-8 is the
            only valid charset here.
            '''
            query = request.data  # get the raw request
            if query is None:
                return Response(
                    'Your POST request to PROMS\' SPARQL endpoint must contain the query in plain text in the '
                    'POST body if the Content-Type \'application/sparql-query\' is used.',
                    status=400
                )

        try:
            if 'SELECT' in query or 'ASK' in query:
                format_mimetype = request.form.get('selectContentType')
            else:
                format_mimetype = request.form.get('graphContentType')

            print(format_mimetype)
            query_result = sparql_query(query, format_mimetype=format_mimetype)
        except ValueError as e:
            return render_template(
                'page_sparql.html',
                query=query,
                query_result='No results: ' + str(e)
            ), 400
        except ConnectionError as e:
            return Response(str(e), status=500)

        # if query_result and 'results' in query_result:
        #     query_result = json.dumps(json.loads(query_result)['results']['bindings'])

        # respond to a form or with a raw result
        if 'form' in request.values and request.values['form'].lower() == 'true':
            return render_template(
                'page_sparql.html',
                query=query,
                query_result=query_result
            )
        else:
            return query_result
            # return Response(json.dumps(query_result), status=200, mimetype=request.values['output-format'])
    # No query, display form
    else:  # GET
        if request.args.get('query') is not None:
            # SPARQL GET request
            '''
            https://www.w3.org/TR/2013/REC-sparql11-protocol-20130321/#query-via-get

            2.1.1 query via GET

            Protocol clients may send protocol requests via the HTTP GET method. When using the GET method, clients must
            URL percent encode all parameters and include them as query parameter strings with the names given above.

            HTTP query string parameters must be separated with the ampersand (&) character. Clients may include the
            query string parameters in any order.

            The HTTP request MUST NOT include a message body.
            '''
            # following check invalid due to higher order if/else
            # if request.args.get('query') is None:
            #     return Response(
            #         'Your GET request to PROMS\' SPARQL endpoint must contain a \'query\' query string argument.',
            #         status=400,
            #         mimetype="text/plain")
            query = request.args.get('query')
            query_result = sparql_query(query)
            return Response(json.dumps(query_result), status=200, mimetype="application/sparql-results+json")
        else:
            # SPARQL Service Description
            '''
            https://www.w3.org/TR/sparql11-service-description/#accessing

            SPARQL services made available via the SPARQL Protocol should return a service description document at the
            service endpoint when dereferenced using the HTTP GET operation without any query parameter strings
            provided. This service description must be made available in an RDF serialization, may be embedded in
            (X)HTML by way of RDFa, and should use content negotiation if available in other RDF representations.
            '''

            acceptable_mimes = [x for x in pyldapi.Renderer.RDF_MIMETYPES] + ['text/html']
            best = request.accept_mimetypes.best_match(acceptable_mimes)
            if best == 'text/html':
                # show the SPARQL query form
                query = request.args.get('query')
                return render_template(
                    'page_sparql.html',
                    query=query
                )
            elif best is not None:
                for item in pyldapi.Renderer.RDF_MIMETYPES:
                    if item == best:
                        path_parts = request.path.rsplit('/', 1)
                        path_parts = list(filter(bool, path_parts))
                        if len(path_parts) == 1:
                            path_parent = '/'
                        else:
                            path_parent = path_parts[0]
                        base_url = request.host_url.rstrip('/') + path_parent
                        rdf_format = best
                        return Response(
                            get_sparql_service_description(
                                format=rdf_format, base_url=base_url),
                            status=200,
                            mimetype=best)

                return Response(
                    'Accept header must be one of ' + ', '.join(acceptable_mimes) + '.',
                    status=400
                )
            else:
                return Response(
                    'Accept header must be one of ' + ', '.join(acceptable_mimes) + '.',
                    status=400
                )


def get_sparql_service_description(format, base_url):
    """Return an RDF description of PROMS' read only SPARQL endpoint in a requested format

    :param mimetype: 'turtle', 'n3', 'xml', 'json-ld'
    :return: string of RDF in the requested format
    """
    sd_ttl = '''\
@prefix rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix sd:     <http://www.w3.org/ns/sparql-service-description#> .
@prefix sdf:    <http://www.w3.org/ns/formats/> .
@prefix void: <http://rdfs.org/ns/void#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<http://linked.data.gov.au/dataset/gnaf/sparql>
    a                       sd:Service ;
    sd:endpoint             <{:s}/sparql> ;
    sd:supportedLanguage    sd:SPARQL11Query ; # yes, read only, sorry!
    sd:resultFormat         sdf:SPARQL_Results_JSON ;  # yes, we only deliver JSON results, sorry!
    sd:feature sd:DereferencesURIs ;
    sd:defaultDataset [
        a sd:Dataset ;
        sd:defaultGraph [
            a sd:Graph ;
            void:triples "100"^^xsd:integer
        ]
    ]
.
'''
    base_url = base_url.rstrip("/")
    sd_ttl = sd_ttl.format(base_url)
    if format == "turtle" or format == "text/turtle":
        return sd_ttl
    g = Graph().parse(io.StringIO(sd_ttl), format='turtle')
    rdf_mimetypes_map = pyldapi.Renderer.RDF_SERIALIZER_MAP
    if format in rdf_mimetypes_map.values():
        return g.serialize(format=format)
    elif format in rdf_mimetypes_map:
        return g.serialize(format=rdf_mimetypes_map[format])
    else:
        raise ValueError('Input parameter rdf_format must be one of: ' + ', '.join(rdf_mimetypes_map.values()))


def sparql_query(sparql_query, format_mimetype='application/sparql-results+json'):
    """ Make a SPARQL query"""
    auth = (config.SPARQL_AUTH_USR, config.SPARQL_AUTH_PWD)
    data = {'query': sparql_query}
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': format_mimetype
    }
    try:
        r = requests.post(config.SPARQL_QUERY_URI, auth=auth, data=data, headers=headers, timeout=30)
        import pprint
        pprint.pprint(r.headers)
        return r.content.decode('utf-8')
    except Exception as e:
        raise e
