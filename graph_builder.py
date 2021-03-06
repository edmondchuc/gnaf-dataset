import logging
import _config as config
import model.address
import model.locality


def get_state_addresses(state_pid):
    cursor = config.get_db_cursor()
    s = '''SELECT address_detail_pid 
           FROM gnaf.address_detail 
           WHERE locality_pid 
           IN (SELECT locality_pid FROM gnaf.locality WHERE state_pid = '{}') 
           ORDER BY address_detail_pid;'''.format(state_pid)
    cursor.execute(s)

    with open('addresses_state_{}.txt'.format(state_pid), 'w') as f:
        for row in cursor.fetchall():
            r = config.reg(cursor, row)
            f.write(str(r.address_detail_pid) + '\n')


def get_localities_in_state(state_pid):
    cursor = config.get_db_cursor()
    s = '''SELECT locality_pid 
           FROM gnaf.locality 
           WHERE state_pid = '{}'
           ORDER BY locality_pid;'''.format(state_pid)
    cursor.execute(s)

    with open('localities_state_{}.txt'.format(state_pid), 'w') as f:
        for row in cursor.fetchall():
            r = config.reg(cursor, row)
            f.write(str(r.locality_pid) + '\n')


def run(index_file, file_id, data_file_count):
    logging.basicConfig(filename='graph_builder.log',
                        level=logging.DEBUG,
                        datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)s %(message)s')

    '''
    - For each Address in the Address Register,
    - Create an Address class instance using the ID
    - Serialise that to a file
    '''
    DATA_FILE_LENGTH_MAX = 100000

    cursor = config.get_db_cursor()

    data_file_stem = 'data-address-'+str(file_id)+"-"
    # for idx, addr in enumerate(cursor.fetchall()):
    for idx, addr in enumerate(open(index_file, 'r').readlines()):
        a = addr.strip()
        try:
            # record the Address being processed in case of failure
            # every DATA_FILE_LENGTH_MAXth URI, create a new destination file
            if (idx + 1) % DATA_FILE_LENGTH_MAX == 0:
                data_file_count += 1
            with open(data_file_stem + str(data_file_count).zfill(4) + '.nt', 'a') as fl:
                fl.write(
                    model.address.Address(a, focus=True, db_cursor=cursor)
                        .export_rdf(view='gnaf').serialize(format='nt').decode('utf-8')
                )
        except Exception as e:
            logging.log(logging.DEBUG, 'address ' + a, e)
            print('address ' + a + '\n')
            print(e)
            with open('faulty.log', 'a') as f:
                f.write(addr + '\n')
        finally:
            logging.log(logging.INFO, 'Last accessed Address: ' + a)


def run_localities(locality_index_file, file_id, data_file_count):
    logging.basicConfig(filename='graph_builder.log',
                        level=logging.DEBUG,
                        datefmt='%Y-%m-%d %H:%M:%S',
                        format='%(asctime)s %(message)s')

    '''
    - For each Address in the Address Register,
    - Create an Address class instance using the ID
    - Serialise that to a file
    '''
    DATA_FILE_LENGTH_MAX = 100000

    cursor = config.get_db_cursor()

    data_file_stem = 'data-locality-'+str(file_id)+"-"
    # for idx, addr in enumerate(cursor.fetchall()):
    for idx, addr in enumerate(open(locality_index_file, 'r').readlines()):
        a = addr.strip()
        try:
            # record the Address being processed in case of failure
            # every DATA_FILE_LENGTH_MAXth URI, create a new destination file
            if (idx + 1) % DATA_FILE_LENGTH_MAX == 0:
                data_file_count += 1
            with open(data_file_stem + str(data_file_count).zfill(4) + '.nt', 'a') as fl:
                rdf = model.locality.Locality(a, db_cursor=cursor)\
                    .export_rdf(view='gnaf').serialize(format='nt').decode('utf-8')
                print(rdf)
                fl.write(
                    rdf
                )
        except Exception as e:
            logging.log(logging.DEBUG, 'address ' + a, e)
            print('locality ' + a + '\n')
            print(e)
            with open('faulty_locality.log', 'a') as f:
                f.write(addr + '\n')
        finally:
            logging.log(logging.INFO, 'Last accessed Locality: ' + a)


if __name__ == '__main__':
    get_state_addresses('1')
    get_state_addresses('2')
    get_state_addresses('3')
    get_state_addresses('4')
    get_state_addresses('5')
    get_state_addresses('6')
    get_state_addresses('7')
    get_state_addresses('8')
    get_state_addresses('9')
    run('addresses_state_1.txt', '1', 1)
    run('addresses_state_2.txt', '2', 1)
    run('addresses_state_3.txt', '3', 1)
    run('addresses_state_4.txt', '4', 1)
    run('addresses_state_5.txt', '5', 1)
    run('addresses_state_6.txt', '6', 1)
    run('addresses_state_7.txt', '7', 1)
    run('addresses_state_8.txt', '8', 1)
    run('addresses_state_9.txt', '9', 1)
    get_localities_in_state('1')
    get_localities_in_state('2')
    get_localities_in_state('3')
    get_localities_in_state('4')
    get_localities_in_state('5')
    get_localities_in_state('6')
    get_localities_in_state('7')
    get_localities_in_state('8')
    get_localities_in_state('9')
    run_localities('localities_state_1.txt', '1', 1)
    run_localities('localities_state_2.txt', '2', 1)
    run_localities('localities_state_3.txt', '3', 1)
    run_localities('localities_state_4.txt', '4', 1)
    run_localities('localities_state_5.txt', '5', 1)
    run_localities('localities_state_6.txt', '6', 1)
    run_localities('localities_state_7.txt', '7', 1)
    run_localities('localities_state_8.txt', '8', 1)
    run_localities('localities_state_9.txt', '9', 1)
