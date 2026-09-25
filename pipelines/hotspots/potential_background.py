"""One consistent global title/year deduplication universe for sensitivity."""
from common import *
import duckdb
c=duckdb.connect();c.execute('SET threads=4');c.execute("SET memory_limit='4GB'")
c.from_parquet(str(BASE/'data/assignments/*.parquet')).create_view('a')
c.execute("""CREATE TEMP TABLE kept AS SELECT row_id,doc_id,source,date FROM (
 SELECT *,regexp_replace(lower(coalesce(title,'')),'[^\\p{L}\\p{N}]','','g') normalized_title
 FROM a WHERE source IN ('paper','patent') AND category_index>=0 AND NOT retracted AND NOT template_record
 AND date BETWEEN '2026-01-01' AND '2026-08-31')
 QUALIFY row_number() OVER(PARTITION BY source,CASE WHEN length(normalized_title)>=15 THEN normalized_title||left(date,4) ELSE doc_id END ORDER BY date,row_id)=1""")
c.sql('SELECT * FROM kept').df().to_parquet(BASE/'data/potential_unified_global_dedup.parquet',index=False)
save(c.sql('SELECT source,left(date,7) AS month,count(*) AS documents FROM kept GROUP BY 1,2').df(),'potential_unified_dedup_denominators.csv')
print('GLOBAL_DEDUP',c.sql('SELECT source,count(*) FROM kept GROUP BY 1').fetchall())
