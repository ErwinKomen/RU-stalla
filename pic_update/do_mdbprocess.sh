#!/bin/bash
APP_NAME="stalla"
LOG="./mdbprocess.log"
NOW=$(date +"%A-%H%M")
HERE="`pwd`"
DBASE="$1"
# Uncomment the appropriate line here, whether on server or local
# Server:
# WRITABLE="/var/www/writable"
# Local development:
WRITABLE="/mnt/d/Data Files/vs2010/projects/writable"
MEDIA="${WRITABLE}/media/stalla/"

echo "Processing MDB on: ${NOW}"              > ${LOG} 2>&1
echo "Home: ${HERE}"                          >> ${LOG} 2>&1
echo "Going to the database backup directory" >> ${LOG} 2>&1
cd "${WRITABLE}/database/bkup/"
echo "Copying current db to bkup"             >> ${LOG} 2>&1
cp ../${APP_NAME}.db .
echo "Zipping ${APP_NAME}.db"                 >> ${LOG} 2>&1
gzip -f ${APP_NAME}.db
echo "Go to MEDIA/stalla dir"                 >> ${LOG} 2>&1
cd "${MEDIA}"


# this is usually mdb_to_json_tables.sh
# Remove earlier JSON file(s)
echo "Removing earlier *.json ..."            >> ${LOG} 2>&1
rm -f *.json

# Iterate through the tables
for table in `mdb-tables ${DBASE}` ; do
  echo "Dealing with table ${table}"          >> ${LOG} 2>&1
  FILENAME=${table}.json
  mdb-json ${DBASE} ${table}  > ${FILENAME}
done

# Indicate that we are done
echo "Done with mdbprocess"                   >> ${LOG} 2>&1
# exit 1