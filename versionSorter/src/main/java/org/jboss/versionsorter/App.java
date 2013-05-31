package org.jboss.versionsorter;

import java.util.ArrayList;
import java.util.Collections;
import org.apache.maven.graph.common.version.VersionSpec;
import org.apache.maven.graph.common.version.VersionUtils;

/**
 * Hello world!
 *
 */
public class App 
{
    public static void main( String[] args ){
		ArrayList<VersionSpec> versions = new ArrayList<>();
		for(String arg : args){
			versions.add(VersionUtils.createFromSpec(arg));
		}
		Collections.sort(versions);
		for(VersionSpec version : versions){
			System.out.println(version.renderStandard());
		}
    }
}
