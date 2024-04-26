import socket
import select
import pickle
import datetime

from typing import *


class ObjectSocketParams:
    """Constants used by ObjectSenderSocket and ObjectReceiverSocket for managing socket connections."""    
    OBJECT_HEADER_SIZE_BYTES = 4
    DEFAULT_TIMEOUT_S = 1
    CHUNK_SIZE_BYTES = 1024


class ObjectSenderSocket:
    """Socket manager for sending objects serialized using pickle over a network connection.

    Attributes:
        ip (str): IP address of the server.
        port (int): Port number of the server.
        sock (socket.socket): Main socket object for network communication.
        conn (socket.socket): Client connection socket once a connection is established.
        print_when_awaiting_receiver (bool): Whether to print a message when waiting for a receiver.
        print_when_sending_object (bool): Whether to print a message when sending an object.
    """
    ip: str
    port: int
    sock: socket.socket
    conn: socket.socket
    print_when_awaiting_receiver: bool
    print_when_sending_object: bool

    def __init__(self, ip: str, port: int,
                 print_when_awaiting_receiver: bool = False,
                 print_when_sending_object: bool = False):
        self.ip = ip
        self.port = port
        """
        Initialize the sender socket and bind it to the specified IP and port.

        Args:
            ip (str): The IP address to bind the server to.
            port (int): The port number to bind the server to.
            print_when_awaiting_receiver (bool): Enable printing status while awaiting a receiver.
            print_when_sending_object (bool): Enable printing status during object sending.
        """

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.bind((self.ip, self.port))
        self.conn = None

        self.print_when_awaiting_receiver = print_when_awaiting_receiver
        self.print_when_sending_object = print_when_sending_object

        self.await_receiver_conection()

    def await_receiver_conection(self):

        """Listen for a connection and establish it once a receiver connects."""
        if self.print_when_awaiting_receiver:
            print(f'[{datetime.datetime.now()}][ObjectSenderSocket/{self.ip}:{self.port}] awaiting receiver connection...')

        self.sock.listen(1)
        self.conn, _ = self.sock.accept()

        if self.print_when_awaiting_receiver:
            print(f'[{datetime.datetime.now()}][ObjectSenderSocket/{self.ip}:{self.port}] receiver connected')

    def close(self):
        """Close the client connection socket."""
        self.conn.close()
        self.conn = None

    def is_connected(self) -> bool:
        """Check whether there is a currently established connection.

        Returns:
            bool: True if the connection is established, otherwise False.
        """
        return self.conn is not None

    def send_object(self, obj: Any):
        """Serialize and send an object over the established connection.

        Args:
            obj (Any): The Python object to send.
        """
        data = pickle.dumps(obj)
        data_size = len(data)
        data_size_encoded = data_size.to_bytes(ObjectSocketParams.OBJECT_HEADER_SIZE_BYTES, 'little')
        self.conn.sendall(data_size_encoded)
        self.conn.sendall(data)
        if self.print_when_sending_object:
            print(f'[{datetime.datetime.now()}][ObjectSenderSocket/{self.ip}:{self.port}] Sent object of size {data_size} bytes.')



class ObjectReceiverSocket:
    """Socket manager for receiving objects serialized using pickle over a network connection.

    Attributes:
        ip (str): IP address of the client.
        port (int): Port number of the client.
        conn (socket.socket): Connection socket to the sender.
        print_when_connecting_to_sender (bool): Whether to print a message when connecting to a sender.
        print_when_receiving_object (bool): Whether to print a message when an object is received.
    """
    ip: str
    port: int
    conn: socket.socket
    print_when_connecting_to_sender: bool
    print_when_receiving_object: bool

    def __init__(self, ip: str, port: int,
                 print_when_connecting_to_sender: bool = False,
                 print_when_receiving_object: bool = False):
        """
        Initialize the receiver socket and connect to the sender's IP and port.

        Args:
            ip (str): IP address to connect to.
            port (int): Port number to connect to.
            print_when_connecting_to_sender (bool): Enable printing status while connecting to the sender.
            print_when_receiving_object (bool): Enable printing status when receiving objects.
        """
        self.ip = ip
        self.port = port
        self.print_when_connecting_to_sender = print_when_connecting_to_sender
        self.print_when_receiving_object = print_when_receiving_object

        self.connect_to_sender()

    def connect_to_sender(self):
        """Establish a connection to the sender."""
        if self.print_when_connecting_to_sender:
            print(f'[{datetime.datetime.now()}][ObjectReceiverSocket/{self.ip}:{self.port}] connecting to sender...')

        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.conn.connect((self.ip, self.port))

        if self.print_when_connecting_to_sender:
            print(f'[{datetime.datetime.now()}][ObjectReceiverSocket/{self.ip}:{self.port}] connected to sender')

    def close(self):
        """Close the connection socket."""
        self.conn.close()
        self.conn = None

    def is_connected(self) -> bool:
        """Check whether there is a currently established connection.

        Returns:
            bool: True if connected, otherwise False.
        """
        return self.conn is not None

    def recv_object(self) -> Any:
        """Receive, deserialize, and return an object from the sender.

        Returns:
            Any: The Python object received and deserialized from the sender.
        """
        obj_size_bytes = self._recv_object_size()
        data = self._recv_all(obj_size_bytes)
        obj = pickle.loads(data)
        if self.print_when_receiving_object:
            print(f'[{datetime.datetime.now()}][ObjectReceiverSocket/{self.ip}:{self.port}] Received object of size {obj_size_bytes} bytes.')
        return obj

    def _recv_with_timeout(self, n_bytes: int, timeout_s: float = ObjectSocketParams.DEFAULT_TIMEOUT_S) -> Optional[bytes]:
        """Receive a specified number of bytes or return None if a timeout occurs.

        Args:
            n_bytes (int): Number of bytes to receive.
            timeout_s (float): Timeout in seconds for the receive operation.

        Returns:
            Optional[bytes]: The received bytes, or None if a timeout occurred.
        """
        rlist, _1, _2 = select.select([self.conn], [], [], timeout_s)
        if rlist:
            data = self.conn.recv(n_bytes)
            return data
        else:
            return None  # Only returned on timeout

    def _recv_all(self, n_bytes: int, timeout_s: float = ObjectSocketParams.DEFAULT_TIMEOUT_S) -> bytes:
        """Receive all specified bytes, handling timeouts and ensuring all data is received.

        Args:
            n_bytes (int): Total number of bytes to receive.
            timeout_s (float): Timeout in seconds for each chunk of data received.

        Returns:
            bytes: All the bytes received.
        """
        data = []
        left_to_recv = n_bytes
        while left_to_recv > 0:
            desired_chunk_size = min(ObjectSocketParams.CHUNK_SIZE_BYTES, left_to_recv)
            chunk = self._recv_with_timeout(desired_chunk_size, timeout_s)
            if chunk is not None:
                data += [chunk]
                left_to_recv -= len(chunk)
            else:  # no more data incoming, timeout
                bytes_received = sum(map(len, data))
                raise socket.error(f'Timeout elapsed without any new data being received. '
                                   f'{bytes_received} / {n_bytes} bytes received.')
        data = b''.join(data)
        return data

    def _recv_object_size(self) -> int:
        """Retrieve the size of the incoming object from the sender.

        Returns:
            int: The size of the object in bytes, as indicated by the header.
        """
        data = self._recv_all(ObjectSocketParams.OBJECT_HEADER_SIZE_BYTES)
        obj_size_bytes = int.from_bytes(data, 'little')
        return obj_size_bytes
