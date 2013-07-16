. tests/testsConfig.sh

check_files_exists(){
   echo "Checking files"
   for a in "$@"; do
      for b in "" ".md5" ".sha1"; do
         if [ ! -f $OUTPUTREPO/$a$b ]; then
            echo "  File $OUTPUTREPO/$a$b not found"
            return 1
         fi
      done
   done
}

check_files_dont_exists(){
   echo "Checking nonexistent files "
   for a in "$@"; do
      for b in "" ".md5" ".sha1"; do
         if [ -f $OUTPUTREPO/$a$b ]; then
            echo "  File $OUTPUTREPO/$a$b was found"
            return 1
         fi
      done
   done
}

check_number_of_files(){
   echo "Checking number of files "
   NUMBER=$(( $1 * 3 )) # each file have .md5 and .sha1
   ACTUAL=$(find test-local-maven-repository/ -type f | wc -l)
   if [ $ACTUAL -ne $NUMBER ]; then
      echo "  Excepted $NUMBER files, but $ACTUAL exists"
      return 1
   fi
}

###################################################################
####################           TESTS           ####################
###################################################################

test_defaults(){
   run 1 || return 1

	RET=0
   check_number_of_files 8 || RET=1

   check_files_exists foo/baz/baz-more/0.1-beta/baz-more-0.1-beta.pom \
                      foo/baz/baz-core/1.2/baz-core-1.2-sources.jar \
                      foo/baz/baz-core/1.2/baz-core-1.2.pom \
                      foo/baz/baz-core/1.2/baz-core-1.2.jar \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5.pom \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5.jar \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5-sources.jar \
                      bar/foo-bar/1.12/foo-bar-1.12.pom \
                      || RET=1
	return $RET
}

test_javadoc_classifier(){
   run 1 -a javadoc || return 1

   RET=0
   check_number_of_files 7 || RET=1

   check_files_exists foo/baz/baz-core/1.2/baz-core-1.2-javadoc.jar \
                      || RET=1

   check_files_dont_exists foo/baz/baz-core/1.2/baz-core-1.2-sources.jar \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5-sources.jar \
                           || RET=1
	return $RET
}

test_all_classifiers(){
   run 1 -a __all__ || return 1

   RET=0
   check_number_of_files 10 || RET=1

   check_files_exists foo/baz/baz-core/1.2/baz-core-1.2-javadoc.jar \
	                   foo/baz/baz-core/1.2/baz-core-1.2-sources.jar \
	                   foo/baz/baz-more/0.1-beta/baz-more-0.1-beta-site.xml \
	                   || RET=1

	return $RET
}

test_multiple_version(){
   run 2 || return 1

   RET=0
   check_number_of_files 14 || RET=1

   check_files_dont_exists foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130202.120000-4.jar \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130202.120000-4-sources.jar \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130202.120000-4.pom \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130102.123000-3.jar \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130101.123000-2.jar \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130101.120000-1.jar \
	                        bar/foo-bar/1.1/foo-bar-1.1.pom \
	                        bar/foo-bar/1.2/foo-bar-1.2.pom \
	                        bar/foo-bar/1.3/foo-bar-1.3.pom \
	                        bar/foo-bar/1.4/foo-bar-1.4.pom \
	                        bar/foo-bar/1.11/foo-bar-1.11.pom \
                           || RET=1

   check_files_exists bar/foo-bar/1.12/foo-bar-1.12.pom \
                      foo/baz/baz-core/1.0/baz-core-1.0.jar \
                      foo/baz/baz-core/1.0/baz-core-1.0.pom \
                      foo/baz/baz-core/1.0/baz-core-1.0-sources.jar \
                      foo/baz/baz-core/1.1/baz-core-1.1.jar \
                      foo/baz/baz-core/1.1/baz-core-1.1.pom \
                      foo/baz/baz-core/1.1/baz-core-1.1-sources.jar \
                      foo/baz/baz-core/1.2/baz-core-1.2.jar \
                      foo/baz/baz-core/1.2/baz-core-1.2.pom \
                      foo/baz/baz-core/1.2/baz-core-1.2-sources.jar \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5.jar \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5.pom \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5-sources.jar \
                      foo/baz/baz-more/0.1-beta/baz-more-0.1-beta.pom \
                      || RET=1
	return $RET
}


test_single_version_false(){
   run 3 || return 1 # "single-version": "false"

   RET=0
   check_number_of_files 25 || RET=1

   check_files_dont_exists foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130202.120000-4.jar \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130202.120000-4-sources.jar \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130202.120000-4.pom \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130102.123000-3.jar \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130101.123000-2.jar \
                           foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130101.120000-1.jar \
                           || RET=1

   check_files_exists bar/foo-bar/1.1/foo-bar-1.1.pom \
                      bar/foo-bar/1.2/foo-bar-1.2.pom \
                      bar/foo-bar/1.3/foo-bar-1.3.pom \
                      bar/foo-bar/1.4/foo-bar-1.4.pom \
                      bar/foo-bar/1.11/foo-bar-1.11.pom \
                      bar/foo-bar/1.12/foo-bar-1.12.pom \
                      foo/baz/baz-core/1.0/baz-core-1.0.jar \
                      foo/baz/baz-core/1.0/baz-core-1.0.pom \
                      foo/baz/baz-core/1.0/baz-core-1.0-sources.jar \
                      foo/baz/baz-core/1.1/baz-core-1.1.jar \
                      foo/baz/baz-core/1.1/baz-core-1.1.pom \
                      foo/baz/baz-core/1.1/baz-core-1.1-sources.jar \
                      foo/baz/baz-core/1.2/baz-core-1.2.jar \
                      foo/baz/baz-core/1.2/baz-core-1.2.pom \
                      foo/baz/baz-core/1.2/baz-core-1.2-sources.jar \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5.jar \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5.pom \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5-sources.jar \
                      foo/baz/baz-more/0.1-beta/baz-more-0.1-beta.pom \
                      || RET=1
	return $RET
}

test_generate_metadata(){
   run 1 -m || return 1

	RET=0
   check_number_of_files 12 || RET=1 # 8 + 4 metadata

   check_files_exists foo/baz/baz-more/maven-metadata.xml \
                      foo/baz/baz-core/maven-metadata.xml \
                      foo/baz/baz-lore/maven-metadata.xml \
                      bar/foo-bar/maven-metadata.xml \
                      || RET=1
	return $RET
}

test_included_gav_patterns(){
	run 4 || return 1

	RET=0
	check_number_of_files 7 || RET=1

	check_files_exists bar/foo-bar/1.12/foo-bar-1.12.pom \
	                   foo/baz/baz-core/1.2/baz-core-1.2.jar \
	                   foo/baz/baz-core/1.2/baz-core-1.2.pom \
	                   foo/baz/baz-core/1.2/baz-core-1.2-sources.jar \
	                   foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5.jar \
	                   foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5.pom \
	                   foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5-sources.jar \
	                   || RET=1
	return $RET
}

test_included_gav_patterns_2(){
	run 5 || return 1

	RET=0
	check_number_of_files 4 || RET=1

	check_files_exists foo/baz/baz-core/1.1/baz-core-1.1.jar \
	                   foo/baz/baz-core/1.1/baz-core-1.1.pom \
	                   foo/baz/baz-core/1.1/baz-core-1.1-sources.jar \
	                   foo/baz/baz-more/0.1-beta/baz-more-0.1-beta.pom \
	                   || RET=1
	return $RET
}

test_excluded_gav_patterns(){
	run 6 || return 1

	RET=0
	check_number_of_files 5 || RET=1

	check_files_exists bar/foo-bar/1.9/foo-bar-1.9.pom || RET=1

	echo "Checking if there is no SNAPSHOT version in repository"
	find test-local-maven-repository/ -type d | grep "SNAPSHOT" && RET=1

	return $RET
}


test_remote_defaults(){
   run 1r || return 1

	RET=0
   check_number_of_files 8 || RET=1

   check_files_exists foo/baz/baz-more/0.1-beta/baz-more-0.1-beta.pom \
                      foo/baz/baz-core/1.2/baz-core-1.2-sources.jar \
                      foo/baz/baz-core/1.2/baz-core-1.2.pom \
                      foo/baz/baz-core/1.2/baz-core-1.2.jar \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5.pom \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5.jar \
                      foo/baz/baz-lore/2.2-SNAPSHOT/baz-lore-2.2-20130505.010020-5-sources.jar \
                      bar/foo-bar/1.12/foo-bar-1.12.pom \
                      || RET=1
	return $RET
}


