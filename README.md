# File-Cast

A peer-to-peer file sharing tool built on a custom BitTorrent-style protocol. Files are split into SHA-1 verified pieces, advertised through a BitTorrent DHT, and discovered on the local network over UDP broadcasts. It ships with both a Kivy GUI and an asyncio command line client.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Kivy](https://img.shields.io/badge/Kivy-GUI-00A0B0?style=flat-square)
![asyncio](https://img.shields.io/badge/asyncio-networking-4B8BBE?style=flat-square)
![DHT](https://img.shields.io/badge/BitTorrent-DHT-2E7D32?style=flat-square)

## How it works

- A file is read in fixed-size pieces (default 256 KB). Each piece is hashed with SHA-1.
- The piece hashes are hashed again to produce a torrent ID that identifies the file.
- The torrent ID is announced to a public BitTorrent DHT so other peers can find a seeder.
- On a LAN, seeders also broadcast a UDP beacon, so peers can discover each other without a tracker.
- Downloads pull pieces over TCP, verify each piece against its hash, then reassemble the file.

## Wire protocol

Every message is length-prefixed: `[4-byte big-endian length][1-byte type][payload]`.

| Type | Name      | Direction | Purpose                                  |
| ---- | --------- | --------- | ---------------------------------------- |
| `L`  | List      | client -> peer | Request the list of hosted files    |
| `M`  | Metadata  | client -> peer | Request the metadata for a torrent  |
| `H`  | Handshake | both      | Confirm both sides share the torrent ID  |
| `B`  | Bitfield  | peer -> client | Which pieces the peer has            |
| `R`  | Request   | client -> peer | Ask for a specific piece             |
| `P`  | Piece     | peer -> client | Send the requested piece             |

Metadata is stored as `metadata.json` next to the piece files and contains the file name, length, piece length, piece hashes, and the torrent ID.

## Layout

- `main_gui.py` - Kivy application (desktop and Android targets). Includes seeding, direct connect, nearby peer scan, and download UI.
- `peer.py` - command line peer. Runs the server loop and can download from peers or the DHT.
- `storage.py` - splits a file into pieces and writes `metadata.json`.

## Running the CLI

Seed a file:

```bash
python storage.py /path/to/file.mp4
python peer.py --port 6881
```

List what a peer is sharing or download by torrent ID:

```bash
python peer.py --peers 192.168.1.5:6881
python peer.py --download <torrent_id>
```

## Running the GUI

```bash
pip install kivy aiobtdht
python main_gui.py
```

## Dependencies

- Python 3.10+
- `kivy` for the GUI
- `aiobtdht` for DHT support (optional, DHT is disabled if the import fails)

## Known limitations

- Downloads currently use the first peer returned by the DHT instead of pulling pieces from multiple peers in parallel.
- Piece storage keeps every piece as a separate file on disk.
- No NAT traversal or UPnP, so peers behind strict NAT cannot accept inbound connections.
- `peer.py` reassembles a download only after every piece is present.
