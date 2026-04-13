#!/usr/bin/env python3
"""
========================================================
标准(7,4)汉明码 - 纠缠共振纠正实验
========================================================

正确实验：
1. 生成随机正确标准汉明码
2. 注入一个单位错误
3. 计算校验子，定位错误位
4. 纠缠共振：翻转错误位和与之纠缠的位
5. 观测：是否回到正确状态

纠缠模型：
- D0(0) ↔ P0(1)
- D1(3) ↔ P0(1), P2(4)
- D2(5) ↔ P1(2), P2(4)
- D3(6) ↔ P1(2)
- P0(1) ↔ D0(0), D1(3), D3(6)
- P1(2) ↔ D0(0), D2(5), D3(6)
- P2(4) ↔ D1(3), D2(5)
"""

import numpy as np
from datetime import datetime

class EntanglementResonance:
    def __init__(self):
        # 数据位→校验位纠缠
        self.data_to_parity = {
            0: [1],       # D0 → P0
            3: [1, 4],    # D1 → P0, P2
            5: [2, 4],    # D2 → P1, P2
            6: [2],       # D3 → P1
        }

        # 校验位→数据位纠缠
        self.parity_to_data = {
            1: [0, 3, 6], # P0 → D0, D1, D3
            2: [0, 5, 6], # P1 → D0, D2, D3
            4: [3, 5],    # P2 → D1, D2
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  标准(7,4)汉明码 - 纠缠共振纠正实验")
        print("=" * 60)
        print(f"数据→校验: {self.data_to_parity}")
        print(f"校验→数据: {self.parity_to_data}")

    def encode(self, data):
        D0, D1, D2, D3 = data[0], data[1], data[2], data[3]
        code = [0] * 7
        code[0] = D0
        code[3] = D1
        code[5] = D2
        code[6] = D3
        code[1] = D0 ^ D1 ^ D3
        code[2] = D0 ^ D2 ^ D3
        code[4] = D1 ^ D2 ^ D3
        return code

    def syndrome(self, code):
        s0 = code[1] ^ code[0] ^ code[3] ^ code[6]
        s1 = code[2] ^ code[0] ^ code[5] ^ code[6]
        s2 = code[4] ^ code[3] ^ code[5] ^ code[6]
        return (s2 << 2) | (s1 << 1) | s0

    def get_error_pos(self, syndrome):
        mapping = {1:1, 2:2, 3:0, 4:4, 5:3, 6:5, 7:6}
        return mapping.get(syndrome)

    def get_entangled(self, error_pos):
        """获取与error_pos纠缠的所有位"""
        entangled = set()

        if error_pos in self.data_to_parity:
            entangled.update(self.data_to_parity[error_pos])

        if error_pos in self.parity_to_data:
            entangled.update(self.parity_to_data[error_pos])

        entangled.discard(error_pos)
        return list(entangled)

    def resonance_flip(self, code, error_pos):
        """纠缠共振翻转"""
        new_code = code.copy()
        entangled = self.get_entangled(error_pos)

        new_code[error_pos] ^= 1
        for pos in entangled:
            new_code[pos] ^= 1

        return new_code, [error_pos] + entangled

    def hamming_correct(self, code):
        """标准汉明码纠正"""
        new_code = code.copy()
        syndrome = self.syndrome(code)
        error_pos = self.get_error_pos(syndrome)

        if error_pos is not None:
            new_code[error_pos] ^= 1

        return new_code, syndrome, error_pos

    def run_trial(self):
        data = [np.random.randint(0, 2) for _ in range(4)]
        original = self.encode(data)

        with_error = original.copy()
        error_pos = np.random.randint(0, 7)
        with_error[error_pos] ^= 1

        syndrome = self.syndrome(with_error)
        detected_pos = self.get_error_pos(syndrome)

        after_resonance, flipped = self.resonance_flip(with_error, error_pos)

        after_hamming, _, _ = self.hamming_correct(with_error)

        resonance_corrected = (after_resonance == original)
        hamming_corrected = (after_hamming == original)

        return {
            'data': data,
            'original': original,
            'error_pos': error_pos,
            'with_error': with_error,
            'syndrome': syndrome,
            'detected_pos': detected_pos,
            'flipped': flipped,
            'after_resonance': after_resonance,
            'after_hamming': after_hamming,
            'resonance_corrected': resonance_corrected,
            'hamming_corrected': hamming_corrected,
        }

    def run(self, n=100):
        print(f"\n运行 {n} 次试验...")
        results = []
        for i in range(n):
            results.append(self.run_trial())
            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n}")
        return results

    def analyze(self, results):
        total = len(results)
        n_res = sum(1 for r in results if r['resonance_corrected'])
        n_ham = sum(1 for r in results if r['hamming_corrected'])
        n_detected = sum(1 for r in results if r['detected_pos'] == r['error_pos'])

        print(f"\n{'='*60}")
        print("  实验结果分析")
        print(f"{'='*60}")
        print(f"\n总实验: {total}")
        print(f"错误被检测: {n_detected}/{total} = {n_detected/total*100:.1f}%")
        print(f"共振纠正: {n_res}/{total} = {n_res/total*100:.1f}%")
        print(f"汉明码纠正: {n_ham}/{total} = {n_ham/total*100:.1f}%")

        return {'total': total, 'n_res': n_res, 'n_ham': n_ham, 'n_detected': n_detected}

    def show_examples(self, results, n=6):
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")
        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  数据:   {r['data']}")
            print(f"  原始码: {r['original']}")
            print(f"  错误位: {r['error_pos']}")
            print(f"  错误码: {r['with_error']}")
            print(f"  校验子: {r['syndrome']} → 检测位{r['detected_pos']}")
            print(f"  纠缠翻转: {r['flipped']}")
            print(f"  共振后: {r['after_resonance']} → {'纠正' if r['resonance_corrected'] else '未纠正'}")
            print(f"  汉明码: {r['after_hamming']} → {'纠正' if r['hamming_corrected'] else '未纠正'}")


def main():
    exp = EntanglementResonance()
    results = exp.run(n=100)
    exp.show_examples(results, n=6)
    a = exp.analyze(results)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    print(f"共振纠正率: {a['n_res']/a['total']*100:.1f}%")
    print(f"汉明码纠正率: {a['n_ham']/a['total']*100:.1f}%")

    if a['n_res'] == 0 and a['n_ham'] == 100:
        print("\n✓ 共振不能纠正错误，而是进入新稳态")
    elif a['n_res'] == 100 and a['n_ham'] == 100:
        print("\n✓ 共振与汉明码效果相同")


if __name__ == "__main__":
    main()