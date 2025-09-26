import asyncio, os, json, argparse, struct
from hashlib import sha1


# Each packet we sending has certain messages like:
# HANDSHAKE : H --- Initial msg sent to ensure the peer replies back and exchanges the torrent_id
# BITFIELD  : B --- Returns the bitfield which is an array of booleans telling which piece of file is present or not
# REQUEST   : R --- Asks the peer to send a required piece of file
# PIECE     : P --- Sends the required piece

MSG_LEN = 4


# packs msg by including the type of msg it is (H, B, R, P) and the payload which is the data of the msg
def pack_msg(msg_type: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(msg_type + payload)) + msg_type + payload



# Helper func to read the msg
# reads the msg
# separates the type and payload and returns
async def read_msg(reader):
    raw_len = await reader.readexactly(MSG_LEN)

    (l,) = struct.unpack(">I", raw_len)

    data = await reader.readexactly(l)

    typ = data[:1]
    payload = data[1:]

    return typ, payload


# ==================== Server shii ======================= #

async def handle_peer(reader, writer, metadata, pieces_dir, bitfield):
    peer_address = writer.get_extra_info('peername') # getting the address (IP:PORT) of the peer

    try:

        # Handshake

        typ, payload = await read_msg(reader= reader)

        if typ != b'H':
            return
        
        client_tId = payload.decode()

        # Checking if torrent_id matches
        if client_tId != metadata["torrent_id"]:
            return
        
        # Sending handshake back if torrent_id matches

        writer.write(pack_msg(b'H', metadata["torrent_id"].encode()))
        await writer.drain()

        # Sending Bitfield

        n_pieces = len(metadata["pieces"])

        bitfield_bytes = bytearray((n_pieces + 7) // 8)

        for i in range(n_pieces):
            if bitfield[i]: # checking if that particular (i-th) piece is available
                byte_idx = i // 8   # tells the index of byte like every byte is 8 bits thats why divide by 8
                bit_idx = i % 8     # tells the index of bit becuase after every 8 bits new byte starts

                bitfield_bytes[byte_idx] |= (1 << bit_idx)  # ok i dont know whatever shii is happening here tell me too plax

        writer.write(pack_msg(b'B', bytes(bitfield_bytes)))       
        await writer.drain()



        # Serving pieces
        
        while True:

            typ, payload = await read_msg(reader= reader)

            # Request

            if typ == b'R':
                (piece_idx,) = struct.unpack(">I", payload[:4])

                if not bitfield[piece_idx]:
                    return
                
                # getting path of piece and opening it, reading it and sending the read data

                piece_path = os.path.join(pieces_dir, f"piece_{piece_idx:06d}.bin")

                with open(piece_path, "rb") as pf:
                    piece_data = pf.read()
                
                # Piece

                writer.write(pack_msg(b'P', struct.pack(">I", piece_idx) + piece_data))
                await writer.drain()


    except asyncio.IncompleteReadError:
        pass
    finally:
        writer.close()
        await writer.wait_closed()



async def start_server_shii(metadata, pieces_dir, bitfield, host, port):
    server = await asyncio.start_server(
        lambda r, w: handle_peer(r, w, 
                                 metadata= metadata, 
                                 pieces_dir= pieces_dir,
                                 bitfield= bitfield),
        host= host,
        port= port
    )

    print(f"Serving on {host}:{port}")

    async with server:
        await server.serve_forever()





# ================== Client shii ========================= #

async def download_from_peer(peer_host, peer_port, metadata, bitfield, pieces_dir):
    n_pieces = len(metadata["pieces"])

    reader, writer = await asyncio.open_connection(peer_host, peer_port)

    try:
        
        # Handshake

        writer.write(pack_msg(b'H', metadata["torrent_id"].encode()))
        await writer.drain()

        typ, payload = await read_msg(reader= reader)

        if typ != b'H':
            return
        
        # Bitfield

        typ, payload = await read_msg(reader= reader)

        if typ != b'B':
            return
        
        peer_bitfield = [False] * n_pieces   # initialize bitfield with all false at start
 
        for i in range(n_pieces):
            byte_idx = i // 8
            bit_idx = i % 8

            if byte_idx < len(payload):
                peer_bitfield[i] = bool(payload[byte_idx] & (1 << bit_idx)) # ok i again dont know whatever shii is going on here

        # Request missing pieces

        for i in range(n_pieces):

            if bitfield[i]: # Piece already present so we skip it
                continue

            if not peer_bitfield[i]: # Peer does not have the piece
                continue

            # Request

            writer.write(pack_msg(b'R', struct.pack(">I", i)))
            await writer.drain()

            # Piece

            typ, payload = await read_msg(reader= reader)

            if typ != b'P':
                continue

            (recv_idx,) = struct.unpack(">I", payload[:4])

            if recv_idx != i: # Did not receive right piece
                continue

            piece_data = payload[4:]

            # Saving piece

            piece_path = os.path.join(pieces_dir, f"piece_{i:06d}.bin")

            with open(piece_path, "wb") as f:
                f.write(piece_data)
            
            # Verifying hash of file to check

            expected = metadata["pieces"][i]

            got = sha1(piece_data).hexdigest()

            if got != expected:
                print(f"SHA missmatch piece {i}")
            else:
                bitfield[i] = True
                print(f"Downloaded piece {i + 1}/{n_pieces} from {peer_host}:{peer_port}")



        # Check if we now have all pieces

        if all(bitfield):

            # Assemble the pieces

            out_file = os.path.join(os.path.dirname(pieces_dir), "downloaded_" + metadata["name"])
            with open(out_file, "wb") as out:
                for i in range(len(metadata["pieces"])):
                    piece_path = os.path.join(pieces_dir, f"piece_{i:06d}.bin")
                    with open(piece_path, "rb") as pf:
                        out.write(pf.read())
            print(f"All pieces downloaded. File assembled at: {out_file}")


    finally:
        writer.close()
        await writer.wait_closed()



# =========================== Main ================================== #

async def main(torrent_dir, port, peers):
    meta_path = os.path.join(torrent_dir, "metadata.json")
    pieces_dir = os.path.join(torrent_dir, "pieces")
    os.makedirs(pieces_dir, exist_ok= True)

    # reading torrent metadata

    with open(meta_path, "r") as f:
        metadata = json.load(f)

    n_pieces = len(metadata["pieces"])
    bitfield = [False] * n_pieces   # initializing bitfield

    # Marking already existing pieces

    for fname in os.listdir(pieces_dir):
        if fname.startswith("piece_"):
            idx = int(fname[6:12])
            bitfield[idx] = True

    host = "0.0.0.0"

    # Start Server

    server_task = asyncio.create_task(
        start_server_shii(
            metadata= metadata,
            pieces_dir= pieces_dir,
            bitfield= bitfield,
            host= host,
            port= port
        )
        )


    # Add all client tasks

    client_tasks = []


    # Adding all peers who want to download

    for peer in peers:
        phost, pport = peer.split(":")
        client_tasks.append(
            download_from_peer(
                peer_host= phost,
                peer_port= int(pport),
                metadata= metadata,
                bitfield= bitfield,
                pieces_dir= pieces_dir
            )
            )
        

    # Run all shii

    await asyncio.gather(server_task, *client_tasks)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--torrent", required= True)
    parser.add_argument("--port", default= 6881, type= int)
    parser.add_argument("--peers", default= "", help= "Comma separated host:port")

    args = parser.parse_args()

    peers = [x for x in args.peers.split(",") if x]

    asyncio.run(main(args.torrent, args.port, peers))

