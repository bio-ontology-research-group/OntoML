package org.mowl.Projectors

// OWL API imports
import org.semanticweb.owlapi.model._
import org.semanticweb.owlapi.apibinding.OWLManager
import org.semanticweb.owlapi.model.parameters.Imports
import uk.ac.manchester.cs.owl.owlapi._
import org.semanticweb.elk.owlapi.ElkReasonerFactory
//import org.semanticweb.owlapi.reasoner.InferenceType

//import org.semanticweb.owlapi.util._

// Java imports
import java.io.File


import collection.JavaConverters._
import org.mowl.Types._


class TaxonomyProjector(var bidirectional_taxonomy: Boolean = false) extends AbstractProjector{

  def projectAxiom(go_class: OWLClass, axiom: OWLClassAxiom): List[Triple] = {
    val axiomType = axiom.getAxiomType().getName()
    axiomType match {
      case "SubClassOf" => {
	val ax = axiom.asInstanceOf[OWLSubClassOfAxiom]
	projectSubClassAxiom(ax.getSubClass.asInstanceOf[OWLClass], ax.getSuperClass)
      }
      case _ => Nil
    }
  }





  def projectSubClassAxiom(go_class: OWLClass, superClass: OWLClassExpression): List[Triple] = {

    val superClass_type = superClass.getClassExpressionType().getName()

    superClass_type match {

      case "Class" => {
	val dst = superClass.asInstanceOf[OWLClass]
        if (bidirectional_taxonomy){
	  new Triple(go_class, "subclassOf", dst) :: new Triple(dst, "superclassOf", go_class) :: Nil
        }else{
          new Triple(go_class, "subclassOf", dst) :: Nil
        }
      }
      case _ => Nil

    }

  }


 def projectWithTransClosure(ontology: OWLOntology) = {
   val imports = Imports.fromBoolean(false)

   val ontClasses = ontology.getClassesInSignature(imports).asScala.toList
   printf("INFO: Number of ontology classes: %d\n", ontClasses.length)

   getTransitiveClosure(ontClasses, ontology)

   val edges = ontClasses.foldLeft(List[Triple]()){(acc, x) => acc ::: processOntClass(x, ontology)}

   edges.asJava
  }


  def getTransitiveClosure(ontClasses:List[OWLClass], ontology: OWLOntology){
    val reasonerFactory = new ElkReasonerFactory();
    val reasoner = reasonerFactory.createReasoner(ontology);

    val superClasses = (cl:OWLClass) => (cl, reasoner.getSuperClasses(cl, false).getFlattened.asScala.toList)

    //aux function
    val transitiveAxioms = (tuple: (OWLClass, List[OWLClass])) => {
      val subclass = tuple._1
      val superClasses = tuple._2
      superClasses.map((sup) => new OWLSubClassOfAxiomImpl(subclass, sup, Nil.asJava))
    }

    //compose aux functions
    val newAxioms = ontClasses flatMap (transitiveAxioms compose  superClasses)

    ontManager.addAxioms(ontology, newAxioms.toSet.asJava)
  }



  // Abstract methods
  def projectAxiom(go_class: OWLClass, axiom: OWLClassAxiom, ontology: OWLOntology): List[Triple] = Nil
  
  
}