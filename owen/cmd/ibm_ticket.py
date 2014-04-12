#!/usr/bin/env python
import os
import prettytable
import sys
import sqlalchemy
import sqlalchemy.sql
from sqlalchemy.orm import sessionmaker

from owen import cli
from owen.db import models as models


class TicketShell(cli.Shell):
    def __init__(self, database):
        database = os.path.abspath(database)
        self.engine = sqlalchemy.create_engine('sqlite:///'+database)
        models.Base.metadata.create_all(self.engine)
        session_class = sessionmaker(bind=self.engine)
        self.session = session_class()

    def _add_obj(self, obj):
        self.session.add(obj)
        self.session.commit()

    def _table(self, query, columns, formatter=None, as_csv=None):
        if not formatter:
            formatter = lambda obj: map(
                lambda col: getattr(obj, col), columns)
        if as_csv:
            print ",".join(columns)
            for obj in query:
                print ",".join(formatter(obj))
        else:
            tbl = prettytable.PrettyTable(columns)
            for obj in query:
                tbl.add_row(formatter(obj))
            print tbl.get_string(border=None)

    @cli.arg('--closed', action='store_true', help='Include closed tickets')
    @cli.arg('--csv', action='store_true', help='Print as CSV')
    def do_ticket_list(self, args):
        q = self.session.query(models.PartRequest)
        if not args.closed:
            q = q.filter(models.PartRequest.closed is not True)
        columns = ['status', 'id', 'hostname', 'model', 'serial', 'part',
                   'fru', 'count', 'ticket_number', 'created on',
                   'closed', 'closed on']

        def row_format(obj):
            empty_none = lambda x: x if x is not None else ''
            row = [obj.status, obj.id, obj.machine.hostname,
                   obj.machine.machine_type, obj.machine.serial,
                   obj.part.description, obj.part.fru, obj.part_count,
                   obj.ticket_number, obj.date_created, obj.closed,
                   obj.date_closed]
            return map(str, map(empty_none, row))
        q.order_by(models.PartRequest.date_created)
        self._table(q.all(), columns, formatter=row_format, as_csv=args.csv)

    @cli.arg('--hostname', required=True, help="Machine hostname")
    @cli.arg('--part', required=True, help="ID of malfunctioning part")
    @cli.arg('--status', help="Optional current status message")
    @cli.arg('--count', help="Number of items requested", default=1)
    def do_ticket_create(self, args):
        machine = self.session.query(models.Machine).\
            filter(models.Machine.hostname == args.hostname).first()
        part = self.session.query(models.Part).\
            filter(models.Part.id == args.part).first()
        if machine and part:
            self._add_obj(models.PartRequest(
                status=args.status, machine=machine,
                part=part, part_count=args.count))
        elif not machine:
            cli.die("Unknown machine hostname %s" % args.hostname)
        elif not part:
            cli.die("Unknown part id %s" % args.part)

    @cli.arg('ticket', help='Ticket ID')
    @cli.arg('--delete', action='store_true', help="Delete the ticket")
    @cli.arg('--status', help="Free-form status message")
    @cli.arg('--number', '-n', help='External ticket-tracking number')
    def do_ticket_alter(self, args):
        q = self.session.query(models.PartRequest).\
            filter(models.PartRequest.id == args.ticket)
        if q.count() != 1:
            cli.die("Unknown ticket: %s" % args.ticket)
        pr = q.first()
        if not pr:
            cli.die("Unknown ticket with id %s" % (args.ticket))
        if args.status:
            pr.status = args.status
        if args.number:
            pr.ticket_number = args.number
        if args.delete:
            q.delete()
        self.session.commit()

    @cli.arg('ticket', help='Ticket ID')
    def do_ticket_close(self, args):
        pr = self.session.query(models.PartRequest).filter(
            models.PartRequest.id == args.ticket).first()
        if not pr:
            cli.die("Unknown ticket with id %s" % (args.ticket))
        pr.close()
        self.session.commit()

    def do_part_list(self, args):
        q = self.session.query(models.Part).order_by(models.Part.id)
        self._table(q, ['id', 'fru', 'description'])

    @cli.arg('--desc', required=True, help='description of the part')
    @cli.arg('--fru', help='FRU number')
    def do_part_create(self, args):
        self._add_obj(models.Part(description=args.desc, fru=args.fru))

    @cli.arg('part', help='part id')
    @cli.arg('--desc', help='description of the part')
    @cli.arg('--fru', help='FRU number')
    @cli.arg('--delete', action='store_true', help='Delete this entry')
    def do_part_alter(self, args):
        q = self.session.query(models.Part).filter(models.Part.id == args.part)
        part = q.first()
        if not part:
            cli.die("Unknown part with id %s" % (args.part))
        if args.desc:
            part.description = args.desc
        if args.fru:
            part.fru = args.fru
        if args.delete:
            pr_count = self.session.query(models.PartRequest).\
                filter(models.PartRequest.part_id == args.part).count()
            if pr_count != 0:
                cli.die("Delete failed: Part %s associated with %d tickets!" %
                        (args.part, pr_count))
            q.delete()
        self.session.commit()

    def do_host_list(self, args):
        q = self.session.query(models.Machine).order_by(models.Machine.id)
        self._table(q, ['id', 'hostname', 'machine_type', 'serial'])

    @cli.arg('hostname', help='Hostname of the machine')
    @cli.arg('machine_type', help='Machine model number')
    @cli.arg('serial', help='Serial number of the machine')
    def do_host_create(self, args):
        self._add_obj(models.Machine(hostname=args.hostname,
                      machine_type=args.machine_type, serial=args.serial))

    @cli.arg('hostname', help='Hostname of the machine')
    @cli.arg('--type', '-t', help='Machine model number')
    @cli.arg('--serial', '-s', help='Serial number of the machine')
    @cli.arg('--delete', '-d', action='store_true', help='Delete this entry')
    def do_host_alter(self, args):
        q = self.session.query(models.Machine).\
            filter(models.Machine.hostname == args.hostname)
        m = q.first()
        if args.type:
            m.machine_type = args.type
        if args.serial:
            m.serial = args.serial
        if args.delete:
            count = self.session.query(models.PartRequest).\
                filter(models.PartRequest.machine_id == args.id).count()
            if count > 0:
                cli.die("Delete failed: Machine %s associated with %d tickets!"
                        % (args.id, count))
            q.delete()
            self.session.commit()


def main():
    DEFAULT_DB_PATH = os.path.join(os.environ.get('HOME'), '.owen.sqlite')
    shell = TicketShell(DEFAULT_DB_PATH)
    shell.main(sys.argv[1:])

if __name__ == '__main__':
    main()
