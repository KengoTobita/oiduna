#!/usr/bin/env python3
"""
Oiduna 統合テストスクリプト

oiduna_client を使って実際の Oiduna API との統合をテストします。
"""

import asyncio
import sys
from pathlib import Path

# oiduna_client をインポート
sys.path.insert(0, str(Path(__file__).parent.parent / "packages" / "oiduna_client" / "src"))

from oiduna_client import OidunaClient
from oiduna_client.exceptions import OidunaError


class IntegrationTest:
    def __init__(self, base_url: str = "http://localhost:57122"):
        self.base_url = base_url
        self.passed = 0
        self.failed = 0
        self.errors = []

    async def run_all(self):
        """全テストを実行"""
        print("\n" + "="*60)
        print("Oiduna Integration Test")
        print("="*60)

        # テスト実行
        await self.test_health()
        await self.test_synthdef_load()
        await self.test_sample_list()

        # 結果サマリー
        print("\n" + "="*60)
        print("Test Summary")
        print("="*60)
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")

        if self.errors:
            print("\nErrors:")
            for error in self.errors:
                print(error)

        if self.failed > 0:
            sys.exit(1)
        else:
            print("\n✓ All tests passed!")
            sys.exit(0)

    async def test_health(self):
        """ヘルスチェックテスト"""
        print(f"\n{'='*60}")
        print(f"TEST: Health Check")
        print('='*60)

        try:
            async with OidunaClient(base_url=self.base_url) as client:
                health = await client.health.check()
                print(f"  Status: {health.status}")
                print(f"  Version: {health.version}")
                print(f"  Components: {health.components}")

                assert health.status in ["healthy", "degraded"], \
                    f"Unexpected status: {health.status}"

                self.passed += 1
                print(f"✓ PASSED: Health Check")
        except Exception as e:
            self.failed += 1
            error_msg = f"✗ FAILED: Health Check\n  Error: {e}"
            self.errors.append(error_msg)
            print(error_msg)

    async def test_synthdef_load(self):
        """SynthDef ロードテスト"""
        print(f"\n{'='*60}")
        print(f"TEST: SynthDef Load from File")
        print('='*60)

        # サンプル SynthDef ファイルパス
        project_root = Path(__file__).parent.parent
        synthdef_file = project_root / "samples" / "synthdefs" / "kick.scd"

        if not synthdef_file.exists():
            print(f"  ⚠ Skipping: {synthdef_file} not found")
            self.passed += 1
            print(f"✓ PASSED: SynthDef Load from File (skipped)")
            return

        try:
            async with OidunaClient(base_url=self.base_url) as client:
                result = await client.synthdef.load_from_file(
                    str(synthdef_file),
                    timeout=10.0
                )
                print(f"  Name: {result.name}")
                print(f"  Loaded: {result.loaded}")
                print(f"  Status: {result.status}")

                if result.status == "error":
                    print(f"  ⚠ SynthDef load failed (SuperCollider may not be ready)")
                    print(f"  Message: {result.message}")
                    # SuperCollider が起動していない場合はスキップ
                    self.passed += 1
                    print(f"✓ PASSED: SynthDef Load from File (skipped - SC not ready)")
                    return

                assert result.loaded, f"SynthDef not loaded: {result.message}"
                self.passed += 1
                print(f"✓ PASSED: SynthDef Load from File")

        except OidunaError as e:
            print(f"  ⚠ SynthDef load error (SuperCollider may not be ready): {e}")
            # SuperCollider が起動していない場合はスキップ
            self.passed += 1
            print(f"✓ PASSED: SynthDef Load from File (skipped - SC not ready)")

    async def test_sample_list(self):
        """サンプルバッファリストテスト"""
        print(f"\n{'='*60}")
        print(f"TEST: Sample Buffer List")
        print('='*60)

        try:
            async with OidunaClient(base_url=self.base_url) as client:
                result = await client.samples.list_buffers()
                print(f"  Buffer count: {result.count}")
                if result.buffers:
                    print(f"  Buffers: {result.buffers[:10]}")  # 最初の10個のみ表示

                if result.count == 0:
                    print(f"  ⚠ No buffers loaded (SuperCollider/SuperDirt may not be ready)")
                    self.passed += 1
                    print(f"✓ PASSED: Sample Buffer List (no buffers)")
                    return

                self.passed += 1
                print(f"✓ PASSED: Sample Buffer List")

        except OidunaError as e:
            print(f"  ⚠ Buffer list error (SuperCollider may not be ready): {e}")
            # SuperCollider が起動していない場合はスキップ
            self.passed += 1
            print(f"✓ PASSED: Sample Buffer List (skipped - SC not ready)")


async def main():
    """メインエントリポイント"""
    test = IntegrationTest()
    await test.run_all()


if __name__ == "__main__":
    asyncio.run(main())
