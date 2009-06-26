package br.usp.pcs.dao;

import javax.persistence.EntityManager;

import br.com.caelum.vraptor.ioc.Component;
import br.com.caelum.vraptor.ioc.RequestScoped;

@RequestScoped
@Component
public class Database {

    private final EntityManager entityManager;

    public Database(EMF emf) {
        entityManager = emf.getEntityManager();
    }

    public EntityManager getEntityManager() {
        return entityManager;
    }

}