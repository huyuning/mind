#!/usr/bin/env python3
"""
========================================================
标准(7,4)汉明码 - 纠缠共振纠正实验 v5
========================================================

标准汉明码校验子映射：
- 校验子0：无错误
- 校验子1：位置1 (P0)
- 校验子2：位置2 (P1)
- 校验子3：位置0 (D0)
- 校验子4：位置4 (P2)
- 校验子5：位置3 (D1)
- 校验子6：位置5 (D2)
- 校验子7：位置6 (D3)

实验：
1. 生成正确汉明码
2. 只翻转某数据位影响的校验位
3. 校验子应该指向该数据位
4. 用共振扫描，看数据位是否被纠正
"""

import numpy as np
from datetime import datetime

class HammingEntanglementV5:
    def __init__(self):
        self.data_pos = [0, 3, 5, 6]
        self.parity_pos = [1, 2, 4]

        # 数据位→校验位纠缠
        # D0(0) → P0(1)
        # D1(3) → P0(1), P2(4)
        # D2(5) → P1(2), P2(4)
        # D3(6) → P1(2)
        self.data_to_parity = {
            0: [1],
            3: [1, 4],
            5: [2, 4],
            6: [2],
        }

        # 校验子→位置映射（标准汉明码）
        self.syndrome_to_pos = {
            0: None,
            1: 1,   # P0
            2: 2,   # P1
            3: 0,   # D0
            4: 4,   # P2
            5: 3,   # D1
            6: 5,   # D2
            7: 6,   # D3
        }

        np.random.seed(int(datetime.now().timestamp()) % 100000)

        print("=" * 60)
        print("  标准(7,4)汉明码 - 纠缠共振纠正实验 v5")
        print("=" * 60)

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
        return self.syndrome_to_pos.get(syndrome)

    def resonance_scan(self, code, flip_pos, parities):
        new_code = code.copy()
        for pos in [flip_pos] + parities:
            new_code[pos] ^= 1
        return new_code

    def run_trial(self):
        data = [np.random.randint(0, 2) for _ in range(4)]
        original = self.encode(data)

        flip_pos = np.random.choice([0, 3, 5, 6])
        parities = self.data_to_parity[flip_pos]

        after_inject = original.copy()
        for p in parities:
            after_inject[p] ^= 1

        syndrome = self.syndrome(after_inject)
        syndrome_error_pos = self.get_error_pos(syndrome)
        syndrome_points_to_data = (syndrome_error_pos == flip_pos)

        after_scan = self.resonance_scan(after_inject, flip_pos, parities)

        data_corrected = (after_scan[flip_pos] == original[flip_pos])
        parities_kept = all(after_scan[p] == after_inject[p] for p in parities)

        return {
            'data': data,
            'original': original,
            'flip_pos': flip_pos,
            'parities': parities,
            'after_inject': after_inject,
            'syndrome': syndrome,
            'syndrome_error_pos': syndrome_error_pos,
            'syndrome_points_to_data': syndrome_points_to_data,
            'after_scan': after_scan,
            'data_corrected': data_corrected,
            'parities_kept': parities_kept,
        }

    def run(self, n=100):
        print(f"运行 {n} 次试验...")
        results = []
        for i in range(n):
            results.append(self.run_trial())
            if (i + 1) % 20 == 0:
                print(f"  进度: {i+1}/{n}")
        return results

    def analyze(self, results):
        total = len(results)
        n_syn = sum(1 for r in results if r['syndrome_points_to_data'])
        n_dat = sum(1 for r in results if r['data_corrected'])
        n_par = sum(1 for r in results if r['parities_kept'])

        print(f"\n{'='*60}")
        print("  实验结果分析")
        print(f"{'='*60}")
        print(f"\n总实验: {total}")
        print(f"校验子指向数据位: {n_syn}/{total} = {n_syn/total*100:.1f}%")
        print(f"数据位被纠正: {n_dat}/{total} = {n_dat/total*100:.1f}%")
        print(f"校验位保持修改后: {n_par}/{total} = {n_par/total*100:.1f}%")

        return {'total': total, 'n_syn': n_syn, 'n_dat': n_dat, 'n_par': n_par}

    def show_examples(self, results, n=6):
        print(f"\n{'='*60}")
        print("  典型例子")
        print(f"{'='*60}")
        for i, r in enumerate(results[:n]):
            print(f"\n例子{i+1}:")
            print(f"  数据:   {r['data']}")
            print(f"  原始码: {r['original']}")
            print(f"  数据位: {r['flip_pos']} → 校验位{r['parities']}")
            print(f"  改后码: {r['after_inject']}")
            print(f"  校验子: {r['syndrome']} → 错误位{r['syndrome_error_pos']} → 指向{r['syndrome_points_to_data']}")
            print(f"  频扫后: {r['after_scan']}")
            print(f"  数据纠正: {r['data_corrected']}, 校验位保持: {r['parities_kept']}")


def main():
    exp = HammingEntanglementV5()
    results = exp.run(n=100)
    exp.show_examples(results, n=6)
    a = exp.analyze(results)

    print(f"\n{'='*60}")
    print("  结论")
    print(f"{'='*60}")
    if a['n_syn'] == 100:
        print("✓ 校验子正确指向数据位")
    if a['n_dat'] == 0:
        print("✓ 共振扫描不纠正数据位（进入新稳态）")


if __name__ == "__main__":
    main()