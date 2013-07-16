#!/bin/bash

run_tests(){
	FAILS=0
	TESTS=0

	for TESTNAME in $(declare -F | cut -c12- | grep "^test_"); do
		let TESTS++
		PREVFAILS=$FAILS
		OUT="`$TESTNAME`"
		RET=$?
		if [ $RET -ne 0 ]; then
			echo "======================================================================"
			echo "FAIL: $TESTNAME"
			echo "----------------------------------------------------------------------"
			echo "$OUT"
			echo
			let FAILS++
		fi
	done
}

for TESTFILE in tests/*Tests.sh; do
	. $TESTFILE
done

STARTTIME=`date +%s%N`
run_tests
ENDTIME=`date +%s%N`

DURSEC=$(( ( $ENDTIME - $STARTTIME ) / 1000000000 ))
DURNAN=$(( ( $ENDTIME - $STARTTIME ) - $DURSEC * 1000000000 ))

echo "----------------------------------------------------------------------"
echo "Ran $TESTS tests in $DURSEC.${DURNAN}s"
echo
[ $FAILS -eq 0 ] && echo "OK" || echo "FAILED (failures=$FAILS)"
