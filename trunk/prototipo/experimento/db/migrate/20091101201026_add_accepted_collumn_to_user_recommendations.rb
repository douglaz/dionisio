class AddAcceptedCollumnToUserRecommendations < ActiveRecord::Migration
  def self.up
    add_column :user_recommendations, :accepted, :boolean
  end

  def self.down
    remove_column :user_recommendations, :accepted
  end
end
