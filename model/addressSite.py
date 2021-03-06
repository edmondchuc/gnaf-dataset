# -*- coding: utf-8 -*-
from .model import GNAFModel
from flask import render_template
from rdflib import Graph, URIRef, RDF, XSD, Namespace, Literal, BNode
import _config as config
from psycopg2 import sql


class AddressSite(GNAFModel):
    """
    This class represents an Address Site and methods in this class allow an Address Site to be loaded from the GNAF
    database and to be exported in a number of formats including RDF, according to the 'GNAF Ontology' and an
    expression of the Dublin Core ontology, HTML, XML in the form according to the AS4590 XML schema.
    """

    def __init__(self, identifier):
        self.id = identifier
        self.uri = config.URI_ADDRESS_SITE_INSTANCE_BASE + identifier
        self.address_site_geocode_ids = dict()

    def export_html(self, view='gnaf'):
        # connect to DB
        cursor = config.get_db_cursor()

        if view == 'gnaf':
            # make a human-readable address
            s = sql.SQL('''SELECT 
                        address_type, 
                        address_site_name                       
                    FROM {dbschema}.address_site
                    WHERE address_site_pid = {id}''') \
                .format(id=sql.Literal(self.id), dbschema=sql.Identifier(config.DB_SCHEMA))

            # get just IDs, ordered, from the address_detail table, paginated by class init args
            cursor.execute(s)
            rows = cursor.fetchall()
            for row in rows:
                address_type = row[0]
                address_site_name = row[1]

            # get a list of addressSiteGeocodeIds from the address_site_geocode table
            s2 = sql.SQL('''SELECT 
                        address_site_geocode_pid,
                        geocode_type                
                    FROM {dbschema}.address_site_geocode_view
                    WHERE address_site_pid = {id}''') \
                .format(id=sql.Literal(self.id), dbschema=sql.Identifier(config.DB_SCHEMA))

            # get just IDs, ordered, from the address_detail table, paginated by class init args
            cursor.execute(s2)
            rows = cursor.fetchall()
            for row in rows:
                self.address_site_geocode_ids[row[0]] = row[1].title()

            view_html = render_template(
                'class_addressSite_gnaf.html',
                address_site_pid=self.id,
                address_site_name=address_site_name,
                address_type=address_type,
                address_site_geocode_ids=self.address_site_geocode_ids
            )

        elif view == 'ISO19160':
            view_html = render_template(
                'class_addressSite_ISO19160.html',
            )

        elif view == 'dct':
            s = sql.SQL('''SELECT 
                        address_type, 
                        address_site_name                       
                    FROM {dbschema}.address_site
                    WHERE address_site_pid = {id}''') \
                .format(id=sql.Literal(self.id), dbschema=sql.Identifier(config.DB_SCHEMA))

            # get just IDs, ordered, from the address_detail table, paginated by class init args
            cursor.execute(s)
            for record in cursor:
                address_type = record[0]
                address_site_name = record[1]

            view_html = render_template(
                'class_addressSite_dct.html',
                identifier=self.id,
                title='Address Site' + self.id,
                description=address_site_name,
                source='G-NAF, 2016',
                type='AddressSite'
            )
        else:
            return NotImplementedError("HTML representation of View '{}' is not implemented.".format(view))
        return view_html

    def export_rdf(self, view='ISO19160', format='text/turtle'):
        g = Graph()
        a = URIRef(self.uri)

        if view == 'ISO19160':
            # get the components from the DB needed for ISO19160
            s = sql.SQL('''SELECT 
                        address_type, 
                        address_site_name                       
                    FROM {dbschema}.address_site
                    WHERE address_site_pid = {id}''') \
                .format(id=sql.Literal(self.id), dbschema=sql.Identifier(config.DB_SCHEMA))

            try:
                cursor = config.get_db_cursor()
                # get just IDs, ordered, from the address_detail table, paginated by class init args
                cursor.execute(s)
                for record in cursor:
                    address_type = record[0]
                    address_site_name = record[1]
            except Exception as e:
                print("Uh oh, can't connect to DB. Invalid dbname, user or password?")
                print(e)

            AddressComponentTypeUriBase = 'http://def.isotc211.org/iso19160/-1/2015/Address/code/AddressComponentType/'

            ISO = Namespace('http://def.isotc211.org/iso19160/-1/2015/Address#')
            g.bind('iso19160', ISO)

            g.add((a, RDF.type, ISO.Address))

            ac_site_name = BNode()
            g.add((ac_site_name, RDF.type, ISO.AddressComponent))
            g.add((ac_site_name, ISO.valueInformation, Literal(address_site_name, datatype=XSD.string)))
            g.add((ac_site_name, ISO.type, URIRef(AddressComponentTypeUriBase + 'siteName')))
            g.add((a, ISO.addressComponent, ac_site_name))

        elif view == 'gnaf':
            raise NotImplementedError("RDF Representation of the GNAF View of an addressSite is not yet implemented.")
            # TODO: implement DCT RDF
        elif view == 'dct':
            raise NotImplementedError("RDF Representation of the DCT View of an addressSite is not yet implemented.")
            # TODO: implement DCT RDF
        else:
            raise RuntimeError("Cannot render an RDF representation of that View.")
        return g
