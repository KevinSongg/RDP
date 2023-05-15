import select
import socket
import sys
import queue
import time

last_output = ""
def output(state, command, num1, num2):
    global last_output
    new_output = ""
    if(command == 'ACK'):
        new_output = time.strftime("%a %b %d %X %Z %Y", time.localtime()) + '; ' + state + '; ' + command + '; Acknowledge: ' + str(num1) + '; Window: ' + '5120'
        if (new_output != last_output):
            print(time.strftime("%a %b %d %X %Z %Y", time.localtime()) + '; ' + state + '; ' + command + '; Acknowledge: ' + str(num1) + '; Window: ' + '5120')
        last_output = time.strftime("%a %b %d %X %Z %Y", time.localtime()) + '; ' + state + '; ' + command + '; Acknowledge: ' + str(num1) + '; Window: ' + '5120'
        
    else:
        new_output = time.strftime("%a %b %d %X %Z %Y", time.localtime()) + '; ' + state + '; ' + command + '; Acknowledge: ' + str(num1) + '; Window: ' + '5120'
        if (new_output != last_output):
            print(time.strftime("%a %b %d %X %Z %Y", time.localtime()) + '; ' + state + '; ' + command + '; Sequence: ' + str(num1) + '; Length: '  + str(num2))
        last_output = time.strftime("%a %b %d %X %Z %Y", time.localtime()) + '; ' + state + '; ' + command + '; Acknowledge: ' + str(num1) + '; Window: ' + '5120'
   

def start_server(host, port, r_file, w_file):
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setblocking(0)
    sock.bind((host, port))

    h2 = ('10.10.1.100', 8888)
    file_contents = queue.Queue()
    inputs = [sock]
    outputs = [sock]
    error = []
    
    writing = queue.Queue()
    reading = queue.Queue()
    response = {}
    response['ACK'] = queue.Queue()
    response['DAT'] = queue.Queue()
    not_acked = []
    writable_not_acked = {}
    RECEIVER_WINDOW = 5120
    receiver_ack = 0

    rdp_state = 0
    final_output = -1
    finished = 0
    last_ack_num = ''
    last_recv_num = ''
    command = 'SYN'
    sequence = 0
    length = 0
    
    try:
        with open(r_file, 'r') as f_read:
            with open(w_file, 'a') as f_write:
                for line in f_read:
                    f_write.write(line)
                    for letter in line:
                        file_contents.put(letter)
    except:
        print('Unable to Read File')
    while True:
        readable, writable, exceptional = select.select(inputs, outputs, error, 0.5)
        for sock in writable:
            while(sequence < receiver_ack + 1 and rdp_state != 2):
                if(rdp_state == 1):
                    payload = ""
                    command = 'DAT'
                    while(not file_contents.empty() and len(payload) < 1024):
                        cont = file_contents.get()
                        payload += cont
                    if(file_contents.empty()):
                        rdp_state = 2
                    length = len(payload)
                if (rdp_state == 0):
                    payload = ""
                    if(command == 'FIN'):
                        final_output = sequence
                        rdp_state = 2
                    length = 0
                packet = command + '\n Sequence: ' + str(sequence) + '\n Length: '  + str(length) + '\n\n' + payload
                packet = packet.encode()
                not_acked.append(sequence)
                writable_not_acked[sequence] = packet
                writing.put(packet)
             
                output('send', command, sequence, length)
                if(length == 0):
                    sequence += 1
                sequence += length

            while(not writing.empty()):
                sock.sendto(writing.get(), h2)
            outputs.remove(sock)
            
        for sock in readable:
            packet = sock.recv(5128)
            ack_or_dat = 0
            string = packet.decode()
            data = string.split("\n")
            for char in data:
                if 'SYN' in char or 'DAT' in char or 'FIN' in char:
                    if ack_or_dat == 1:
                        if not response['DAT'].empty():
                            response['DAT'].put(e.split('SYN')[0])
                    response['DAT'].put('SYN' if 'SYN' in char else 'DAT' if 'DAT' in char else 'FIN')
                    ack_or_dat = 1
                elif 'ACK' in char:
                    ack_or_dat = 0
                    response['ACK'].put('ACK')

                else:
                    response['ACK'].put(char) if ack_or_dat == 0 else response['DAT'].put(char)
        
            while(not response['DAT'].empty()):
                temp_command = response['DAT'].get()
                if(temp_command == ""):
                    break
                header1 = response['DAT'].get()
                header1 = header1.split()
             
                header_length = response['DAT'].get()
                header_length = header_length.split()
                sequence_length = int(header1[1])
                read_length = int(header_length[1])
            
                response['DAT'].get()
                if(temp_command != 'DAT'):
                    response['DAT'].get()

                if(temp_command == 'DAT' and read_length > 0):
                    payload = ""
                    while(not response['DAT'].empty() and len(payload) < read_length):
                        payload += response['DAT'].get()
                        if(read_length > len(payload)):
                            payload += '\n'
                            if(len(payload) == read_length):
                                response['DAT'].get()
                if (str(sequence_length) != last_recv_num):
                    output('receive', temp_command, sequence_length, read_length)
                    last_recv_num = str(sequence_length)

                while(sequence_length == receiver_ack):
                    if(read_length == 0):
                        receiver_ack += 1
                    receiver_ack += len(payload)

                packet = 'ACK\n Acknowledge: ' + str(receiver_ack) + '\n Window: '  + str(RECEIVER_WINDOW) + '\n\n'
                packet = packet.encode()
                reading.put(packet)
                
                if (str(receiver_ack) != last_ack_num):
                    output('send', 'ACK', receiver_ack, RECEIVER_WINDOW)
                    last_ack_num = str(receiver_ack)
                    
                if(response['DAT'].empty()):
                    while(not reading.empty()):
                        sock.sendto(reading.get(), h2)
                                 
            while(not response['ACK'].empty()):
                temp_command = response['ACK'].get()
                if(temp_command == ""):
                    break
                header1 = response['ACK'].get()
                header1 = header1.split()
                recv_ack = int(header1[1])

                response['ACK'].get()
                
                if(recv_ack > 0 and rdp_state != 2):
                    rdp_state = 1

                output('receive', temp_command, recv_ack, RECEIVER_WINDOW)
                
                for seq_num in not_acked:
                    if(seq_num < recv_ack):
                        not_acked.remove(seq_num)
                        del writable_not_acked[seq_num]

                if(rdp_state == 2 and len(writable_not_acked) == 0):
                    command = 'FIN'
                    rdp_state = 0
                recv_ack = recv_ack - 1
                if(recv_ack == final_output):
                    inputs.remove(sock)
                    finished = -1
                    break
                outputs.append(sock)
                
        if not (readable or writable or exceptional):
            if (finished == -1):
                break
            last_seq = min(not_acked)
            last_packet = writable_not_acked[last_seq]
            sock.sendto(last_packet, h2)
            continue
    sock.close()
    
if __name__ == '__main__':
    start_server(sys.argv[1], int(sys.argv[2]), sys.argv[3], sys.argv[4])
