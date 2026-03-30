import { createClient, type Client, type ResultSet } from '@libsql/client';

let client: Client | null = null;

export function getClient(): Client {
  if (!client) {
    const url = process.env.TURSO_URL;
    const authToken = process.env.TURSO_AUTH_TOKEN;
    
    if (!url || !authToken) {
      throw new Error('TURSO_URL and TURSO_AUTH_TOKEN must be set');
    }
    
    client = createClient({ url, authToken });
  }
  return client;
}

/**
 * Compatibility wrapper that mimics better-sqlite3's API but uses libsql.
 * This lets us avoid rewriting every API route — just change getDb() calls.
 */
export function getDb() {
  const c = getClient();
  
  return {
    prepare(sql: string) {
      return {
        /**
         * Run query and return all rows as objects.
         */
        all(...params: unknown[]): Promise<Record<string, unknown>[]> {
          return c.execute({ sql, args: params as any }).then(rs => rowsToObjects(rs));
        },
        /**
         * Run query and return first row as object.
         */
        get(...params: unknown[]): Promise<Record<string, unknown> | undefined> {
          return c.execute({ sql, args: params as any }).then(rs => {
            const rows = rowsToObjects(rs);
            return rows[0];
          });
        },
        /**
         * Execute a write query (INSERT/UPDATE/DELETE).
         */
        run(...params: unknown[]): Promise<{ changes: number; lastInsertRowid: number | bigint }> {
          return c.execute({ sql, args: params as any }).then(rs => ({
            changes: rs.rowsAffected,
            lastInsertRowid: rs.lastInsertRowid ?? 0,
          }));
        },
      };
    },
    
    /**
     * Execute raw SQL (for schema creation, etc.)
     */
    async exec(sql: string): Promise<void> {
      // Split by semicolons and execute each statement
      const statements = sql.split(';').map(s => s.trim()).filter(s => s.length > 0);
      for (const stmt of statements) {
        await c.execute(stmt);
      }
    },
  };
}

function rowsToObjects(rs: ResultSet): Record<string, unknown>[] {
  return rs.rows.map(row => {
    const obj: Record<string, unknown> = {};
    rs.columns.forEach((col, i) => {
      obj[col] = row[i];
    });
    return obj;
  });
}
