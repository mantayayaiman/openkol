"""
X-Bogus signature generator for TikTok Web API.
Reverse-engineered from TikTok's obfuscated JS VM.
Based on open-source implementations (Evil0ctal, Johnserf-Seed).
"""
import time
import base64
import hashlib


class XBogus:
    def __init__(self, user_agent: str = None) -> None:
        self.Array = [
            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
            0, 1, 2, 3, 4, 5, 6, 7, 8, 9, None, None, None, None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None, None, None, None, None, None,
            None, None, None, None, None, None, None, None, None, None, None, None, 10, 11, 12, 13, 14, 15
        ]
        self.character = "Dkdpgh4ZKsQB80/Mfvw36XI1R25-WUAlEi7NLboqYTOPuzmFjJnryx9HVGcaStCe="
        self.ua_key = b"\x00\x01\x0c"
        self.user_agent = (
            user_agent
            if user_agent is not None and user_agent != ""
            else "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )

    def md5_str_to_array(self, md5_str):
        if isinstance(md5_str, str) and len(md5_str) > 32:
            return [ord(char) for char in md5_str]
        else:
            array = []
            idx = 0
            while idx < len(md5_str):
                array.append(
                    (self.Array[ord(md5_str[idx])] << 4)
                    | self.Array[ord(md5_str[idx + 1])]
                )
                idx += 2
            return array

    def md5_encrypt(self, url_path):
        return self.md5_str_to_array(
            self.md5(self.md5_str_to_array(self.md5(url_path)))
        )

    def md5(self, input_data):
        if isinstance(input_data, str):
            array = self.md5_str_to_array(input_data)
        elif isinstance(input_data, list):
            array = input_data
        else:
            raise ValueError("Invalid input type")
        md5_hash = hashlib.md5()
        md5_hash.update(bytes(array))
        return md5_hash.hexdigest()

    def encoding_conversion(self, a, b, c, e, d, t, f, r, n, o, i, _, x, u, s, l, v, h, p):
        y = [a]
        y.append(int(i))
        y.extend([b, _, c, x, e, u, d, s, t, l, f, v, r, h, n, p, o])
        return bytes(y).decode("ISO-8859-1")

    def encoding_conversion2(self, a, b, c):
        return chr(a) + chr(b) + c

    def rc4_encrypt(self, key, data):
        S = list(range(256))
        j = 0
        for i in range(256):
            j = (j + S[i] + ord(key[i % len(key)])) % 256
            S[i], S[j] = S[j], S[i]
        
        result = []
        i = j = 0
        for char in data:
            i = (i + 1) % 256
            j = (j + S[i]) % 256
            S[i], S[j] = S[j], S[i]
            result.append(chr(ord(char) ^ S[(S[i] + S[j]) % 256]))
        return "".join(result)

    def calculation(self, a1, a2, a3):
        x1 = (a1 & 255) << 16 | (a2 & 255) << 8 | (a3 & 255)
        return (
            self.character[(x1 & 16515072) >> 18]
            + self.character[(x1 & 258048) >> 12]
            + self.character[(x1 & 4032) >> 6]
            + self.character[x1 & 63]
        )

    def getXBogus(self, url_params):
        array1 = self.md5_str_to_array(
            self.md5(
                self.md5_str_to_array(
                    self.md5(url_params)
                )
            )
        )
        array2 = self.md5_str_to_array(
            self.md5(
                self.md5_str_to_array(
                    self.md5(self.user_agent)
                )
            )
        )
        
        canvas = 0  # canvas fingerprint placeholder
        now = int(time.time())
        
        ct = 536919696
        array3 = []
        array4 = []
        
        new_arr = [
            64, 0.00390625, 1, 12,
            url_params, self.user_agent,
            ct, now, canvas
        ]
        
        # Build array3 (from URL params)
        xb_str = self.md5_str_to_array(self.md5(url_params))
        
        # Build combined
        idx = 0
        for b in range(0, len(array1), 2):
            combined = array1[b] ^ array2[b]
            array3.append(combined)
        for b in range(0, len(array1), 2):
            combined = array1[b + 1] ^ array2[b + 1]
            array4.append(combined)
        
        # Timestamp processing
        t_bytes = [
            (now >> 24) & 255,
            (now >> 16) & 255,
            (now >> 8) & 255,
            now & 255,
        ]
        
        ct_bytes = [
            (ct >> 24) & 255,
            (ct >> 16) & 255,
            (ct >> 8) & 255,
            ct & 255,
        ]
        
        # Canvas hash
        canvas_bytes = [
            (canvas >> 24) & 255,
            (canvas >> 16) & 255,
            (canvas >> 8) & 255,
            canvas & 255,
        ]
        
        # Encoding
        merged = self.encoding_conversion(
            2, 255,
            array1[14], array1[15],
            array2[14], array2[15],
            array3[0], array3[1],
            array3[2], array3[3],
            array3[4], array3[5],
            array3[6], array3[7],
            t_bytes[0], t_bytes[1],
            t_bytes[2], t_bytes[3],
            1
        )

        garbled_code = self.encoding_conversion2(
            64, 0, merged
        )

        xb = base64.b64encode(garbled_code.encode("ISO-8859-1")).decode()
        xb = xb.replace("/", "_").replace("+", "-").replace("=", "")
        
        return f"{url_params}&X-Bogus={xb}", xb
