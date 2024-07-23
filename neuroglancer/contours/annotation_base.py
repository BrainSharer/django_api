from authentication.models import User
from brain.models import Animal
import logging
logging.basicConfig()
logger = logging.getLogger(__name__)


class AnnotationBase:
    """The Base class handling annotation object and session from neuroglancer
       This class contains method that would use the django ORM to check if a user or animal exists and
       set the appropriate attributes with the corresponding django query result
    """

    def set_annotator_from_id(self, user_id):
        """set the annotator attribute of self using the primary key of the user table.  Returns error if the user is not found

        :param user_id: (int) primary key of the user table
        """

        try:
            self.annotator = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            logger.error("User does not exist")
            return

    def set_animal_from_id(self, animal_id):
        """set the animal attribute of self using the primary key of the animal table.  Returns error if animal is not found

        :param animal_id: (int) primary key of the animal table
        """
        
        try:
            self.animal = Animal.objects.get(pk=animal_id)
        except Animal.DoesNotExist:
            logger.error("Animal does not exist")
            return

    def set_animal_from_animal_name(self, animal_name):
        """set the animal attribute of self using the string ID of the animal.  Returns error if animal is not found

        :param animal_name: (str) ID of the animal given by experimentalists
        """
        
        try:
            self.animal = Animal.objects.filter(prep_id=animal_name).first()
        except Animal.DoesNotExist:
            logger.error("Animal does not exist")
            return
