#!/usr/bin/env python3
"""
Test database and cache connections
Run this script to verify PostgreSQL and Redis are properly configured
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_postgresql():
    """Test PostgreSQL connection"""
    print("\n🔍 Testing PostgreSQL connection...")

    try:
        import psycopg2
        from psycopg2 import sql

        # Try to connect
        conn = psycopg2.connect(
            dbname=os.getenv('DB_NAME', 'patreon'),
            user=os.getenv('DB_USER', 'patreon_user'),
            password=os.getenv('DB_PASSWORD', 'CHANGE_THIS_PASSWORD'),
            host=os.getenv('DB_HOST', 'localhost'),
            port=os.getenv('DB_PORT', '5432')
        )

        cursor = conn.cursor()

        # Test basic query
        cursor.execute('SELECT version();')
        version = cursor.fetchone()[0]
        print(f"✅ PostgreSQL connected: {version.split(',')[0]}")

        # Check pgvector extension
        cursor.execute("SELECT * FROM pg_extension WHERE extname = 'vector';")
        if cursor.fetchone():
            print("✅ pgvector extension installed")
        else:
            print("⚠️  pgvector extension NOT found - install with: CREATE EXTENSION vector;")

        # List tables
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()

        if tables:
            print(f"✅ Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table[0]}")
        else:
            print("ℹ️  No tables found (run database/schema.sql to create them)")

        cursor.close()
        conn.close()
        return True

    except ImportError:
        print("❌ psycopg2 not installed - run: pip install psycopg2-binary")
        return False
    except Exception as e:
        print(f"❌ PostgreSQL connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Is PostgreSQL running? sudo systemctl status postgresql")
        print("  2. Is the database created? sudo -u postgres psql -c '\\l'")
        print("  3. Check credentials in .env file")
        return False


def test_redis():
    """Test Redis connection"""
    print("\n🔍 Testing Redis connection...")

    try:
        import redis

        # Try to connect
        r = redis.Redis(
            host=os.getenv('REDIS_HOST', 'localhost'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=0,
            decode_responses=True
        )

        # Test ping
        if r.ping():
            print("✅ Redis connected")

        # Test set/get
        r.set('test_key', 'test_value')
        value = r.get('test_key')
        if value == 'test_value':
            print("✅ Redis read/write working")
            r.delete('test_key')

        # Get info
        info = r.info()
        print(f"✅ Redis version: {info['redis_version']}")
        print(f"   Memory used: {info['used_memory_human']}")

        return True

    except ImportError:
        print("❌ redis not installed - run: pip install redis")
        return False
    except Exception as e:
        print(f"❌ Redis connection failed: {e}")
        print("\nTroubleshooting:")
        print("  1. Is Redis running? sudo systemctl status redis-server")
        print("  2. Check host/port in .env file")
        return False


def test_celery_imports():
    """Test Celery can be imported"""
    print("\n🔍 Testing Celery installation...")

    try:
        import celery
        print(f"✅ Celery installed: {celery.__version__}")
        return True
    except ImportError:
        print("❌ Celery not installed - run: pip install celery[redis]")
        return False


def test_sqlalchemy():
    """Test SQLAlchemy installation"""
    print("\n🔍 Testing SQLAlchemy installation...")

    try:
        import sqlalchemy
        print(f"✅ SQLAlchemy installed: {sqlalchemy.__version__}")

        # Try to create engine
        from sqlalchemy import create_engine
        engine = create_engine(
            f"postgresql://{os.getenv('DB_USER', 'patreon_user')}:"
            f"{os.getenv('DB_PASSWORD', 'CHANGE_THIS_PASSWORD')}@"
            f"{os.getenv('DB_HOST', 'localhost')}:"
            f"{os.getenv('DB_PORT', '5432')}/"
            f"{os.getenv('DB_NAME', 'patreon')}"
        )

        # Test connection
        with engine.connect() as conn:
            result = conn.execute(sqlalchemy.text("SELECT 1"))
            if result.fetchone()[0] == 1:
                print("✅ SQLAlchemy can connect to PostgreSQL")

        return True

    except ImportError:
        print("❌ SQLAlchemy not installed - run: pip install sqlalchemy")
        return False
    except Exception as e:
        print(f"⚠️  SQLAlchemy installed but connection failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 Testing Infrastructure Setup")
    print("=" * 60)

    # Load .env if exists
    try:
        from dotenv import load_dotenv
        if os.path.exists('.env'):
            load_dotenv()
            print("✅ Loaded .env file")
        else:
            print("ℹ️  No .env file found (optional)")
    except ImportError:
        print("ℹ️  python-dotenv not installed (optional)")

    results = {
        'PostgreSQL': test_postgresql(),
        'Redis': test_redis(),
        'Celery': test_celery_imports(),
        'SQLAlchemy': test_sqlalchemy(),
    }

    print("\n" + "=" * 60)
    print("📊 Summary")
    print("=" * 60)

    passed = sum(results.values())
    total = len(results)

    for name, result in results.items():
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print(f"\n{passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed! You're ready to proceed with Phase 0")
        return 0
    else:
        print("\n⚠️  Some tests failed. Fix the issues above before proceeding.")
        return 1


if __name__ == '__main__':
    sys.exit(main())
