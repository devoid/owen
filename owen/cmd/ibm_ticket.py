#!/usr/bin/env python
from datetime import datetime
import collections
import os
import prettytable
import subprocess
import sys
from sqlalchemy.ext.declarative import declarative_base
import sqlalchemy
import sqlalchemy.sql
from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship, backref, sessionmaker


import owen.cli as cli

DEFAULT_DB_PATH = '/root/service_tickets.sqlite'

def warn(error):
    print >>sys.stderr, error

def die(error):
    warn(error)
    sys.exit(1)




## Objects ##
Base = declarative_base()
class Machine(Base):
    __tablename__ = 'machines'
    
    id = Column(Integer, primary_key=True)
    hostname = Column(String)
    machine_type = Column(String)
    serial = Column(String)
    
    def __repr__(self):
        return "<Machine('%s','%s','%s')>" % (
            self.hostname, self.machine_type, self.serial)

class Part(Base):
    __tablename__ = 'parts'
    
    id = Column(Integer, primary_key=True)
    fru = Column(String)
    description = Column(String) 

    def __repr__(self):
        return "<Part('%s','%s')>" % (self.description, self.fru)
    


class PartRequest(Base):
    __tablename__ = 'part_requests'

    id = Column(Integer, primary_key=True)
    closed = Column(Boolean, default=False)
    machine_id = Column(Integer, ForeignKey('machines.id'))
    machine = relationship("Machine",
        backref=backref('part_requests', order_by=id))
    part_id = Column(Integer, ForeignKey('parts.id'))
    part = relationship("Part",
        backref=backref('requested', order_by=id))
    part_count = Column(Integer)
    ticket_number = Column(String)
    status = Column(String)
    date_created = Column(DateTime,
        default=datetime.now(),
        server_default=sqlalchemy.sql.func.current_timestamp())
    date_closed  = Column(DateTime)
    
    def close(self):
        self.closed = True
        self.date_closed = datetime.now()

def get_model_and_serial(host):
    filename = os.path.join(ASU_COLLECTION_DIR, host)
    if not os.path.isfile(filename):
        filename = os.path.join(ASU_COLLECTION_DIR, host + '.conf')
    if not os.path.isfile(filename):
        return ('Unknown','Unknown')
    # Model
    cmd = [ 'grep', 'SYSTEM_PROD_DATA.SysInfoProdName', filename ]
    _, model = subprocess.check_output(cmd).rstrip().split('=')
    # Serial
    cmd = [ 'grep', 'SYSTEM_PROD_DATA.SysInfoSerialNum', filename ]
    _, serial = subprocess.check_output(cmd).rstrip().split('=')
    return (model, serial)

class TicketShell(cli.Shell):
    def __init__(self, database):
        database = os.path.abspath(database)
        self.engine = sqlalchemy.create_engine('sqlite:///'+database) 
        Base.metadata.create_all(self.engine)
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
        q = self.session.query(PartRequest)
        if not args.closed:
            q = q.filter(PartRequest.closed != True)
        columns = [ 'status', 'id', 'hostname', 'model', 'serial', 'part',
                    'fru', 'count', 'ticket_number', 'created on',
                    'closed', 'closed on']
        def row_format(obj):
            empty_none = lambda x: x if x is not None else ''
            return map(str, map(empty_none,
                [ obj.status, obj.id, obj.machine.hostname,
                obj.machine.machine_type, obj.machine.serial,
                obj.part.description, obj.part.fru, obj.part_count,
                obj.ticket_number, obj.date_created, obj.closed,
                obj.date_closed ]))
        q.order_by(PartRequest.date_created)
        self._table(q.all(), columns, formatter=row_format, as_csv=args.csv)

    @cli.arg('--hostname', required=True, help="Machine hostname")
    @cli.arg('--part', required=True, help="ID of malfunctioning part")
    @cli.arg('--status', help="Optional current status message")
    @cli.arg('--count', help="Number of items requested", default=1)
    def do_ticket_create(self, args):
        machine = self.session.query(Machine).\
            filter(Machine.hostname == args.hostname).first()
        part = self.session.query(Part).\
            filter(Part.id == args.part).first()
        if machine and part:
            self._add_obj(PartRequest(
                status=args.status, machine=machine,
                part=part, part_count=args.count))
        elif not machine:
            die("Unknown machine hostname %s" % args.hostname)
        elif not part:
            die("Unknown part id %s" % args.part)
            
    @cli.arg('ticket', help='Ticket ID')
    @cli.arg('--delete', action='store_true', help="Delete the ticket")
    @cli.arg('--status', help="Free-form status message")
    @cli.arg('--number', '-n', help='External ticket-tracking number')
    def do_ticket_alter(self, args):
        q = self.session.query(PartRequest).\
            filter(PartRequest.id == args.ticket)
        if q.count() != 1:
            die("Unknown ticket: %s" % args.ticket)
        pr = q.first()
        if not pr:
           die("Unknown ticket with id %s" % (args.ticket))
        if args.status:
            pr.status = args.status
        if args.number:
            pr.ticket_number = args.number
        if args.delete:
            q.delete()
        self.session.commit()

    @cli.arg('ticket', help='Ticket ID')
    def do_ticket_close(self, args):
        pr = self.session.query(PartRequest).filter(
            PartRequest.id == args.ticket).first()
        if not pr:
           die("Unknown ticket with id %s" % (args.ticket))
        pr.close()
        self.session.commit()

    def do_part_list(self, args):
        self._table(self.session.query(Part).order_by(Part.id),
                    ['id', 'fru', 'description'])
    
    
    @cli.arg('--desc', required=True, help='description of the part') 
    @cli.arg('--fru', help='FRU number')
    def do_part_create(self, args):
        self._add_obj(Part(description=args.desc, fru=args.fru))
        

    @cli.arg('part', help='part id')
    @cli.arg('--desc', help='description of the part') 
    @cli.arg('--fru', help='FRU number')
    @cli.arg('--delete', action='store_true', help='Delete this entry')
    def do_part_alter(self, args):
        q = self.session.query(Part).filter(Part.id == args.part)
        part = q.first()
        if not part:
           die("Unknown part with id %s" % (args.part))
        if args.desc:
            part.description = args.desc
        if args.fru:
            part.fru = args.fru
        if args.delete:
            pr_count = self.session.query(PartRequest).\
                filter(PartRequest.part_id == args.part).count()
            if pr_count != 0:
                die("Delete failed: Part %s associated with %d tickets!" %
                    (args.part, pr_count))
            q.delete()
        self.session.commit()
            

    def do_host_list(self, args):
        self._table(self.session.query(Machine).order_by(Machine.id),
                    ['id', 'hostname', 'machine_type', 'serial'])
    
    
    @cli.arg('hostname', help='Hostname of the machine')
    @cli.arg('machine_type', help='Machine model number')
    @cli.arg('serial', help='Serial number of the machine')
    def do_host_create(self, args):
        self._add_obj(Machine(hostname=args.hostname,
            machine_type=args.machine_type, serial=args.serial))
    
    
    @cli.arg('hostname', help='Hostname of the machine')
    @cli.arg('--type','-t', help='Machine model number')
    @cli.arg('--serial','-s', help='Serial number of the machine')
    @cli.arg('--delete','-d', action='store_true', help='Delete this entry')
    def do_host_alter(self, args):
        q = self.session.query(Machine).\
            filter(Machine.hostname == args.hostname) 
        m = q.first()
        if args.type:
            m.machine_type = args.type
        if args.serial:
            m.serial = args.serial
        if args.delete:
            count = self.session.query(PartRequest).\
                filter(PartRequest.machine_id == args.id).count()
            if count > 0:
                die("Delete failed: Machine %s associated with %d tickets!"
                    % (args.id, count))
            q.delete()
            self.session.commit()

def main():
    shell = TicketShell(DEFAULT_DB_PATH)
    shell.main(sys.argv[1:])

if __name__ == '__main__':
    main()
